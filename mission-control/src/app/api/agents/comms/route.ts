import { NextRequest, NextResponse } from "next/server"
import { getDatabase, Message, db_helpers } from "@/lib/db"
import { requireRole } from '@/lib/auth'
import { logger } from '@/lib/logger'
import { eventBus } from '@/lib/event-bus'

/**
 * GET /api/agents/comms - Inter-agent communication stats and timeline
 * Query params: limit, offset, since, agent
 */
export async function GET(request: NextRequest) {
  const auth = requireRole(request, 'viewer')
  if ('error' in auth) return NextResponse.json({ error: auth.error }, { status: auth.status })

  try {
    const db = getDatabase()
    const { searchParams } = new URL(request.url)
    const workspaceId = auth.user.workspace_id ?? 1

    const limit = parseInt(searchParams.get("limit") || "100")
    const offset = parseInt(searchParams.get("offset") || "0")
    const since = searchParams.get("since")
    const agent = searchParams.get("agent")

    // Session-thread comms feed used by coordinator + runtime sessions
    const commsPredicate = `
      (
        conversation_id LIKE 'a2a:%'
        OR conversation_id LIKE 'coord:%'
        OR conversation_id LIKE 'session:%'
        OR conversation_id LIKE 'agent_%'
        OR (json_valid(metadata) AND json_extract(metadata, '$.channel') = 'coordinator-inbox')
      )
    `

    const humanNames = ["human", "system", "operator"]
    const humanPlaceholders = humanNames.map(() => "?").join(",")

    // 1. Get timeline messages (page latest rows but render chronologically)
    let messagesWhere = `
      FROM messages
      WHERE workspace_id = ?
        AND ${commsPredicate}
    `
    const messagesParams: any[] = [workspaceId]

    if (since) {
      messagesWhere += " AND created_at > ?"
      messagesParams.push(parseInt(since, 10))
    }
    if (agent) {
      messagesWhere += " AND (from_agent = ? OR to_agent = ?)"
      messagesParams.push(agent, agent)
    }

    const messagesQuery = `
      SELECT * FROM (
        SELECT *
        ${messagesWhere}
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?
      ) recent
      ORDER BY created_at ASC, id ASC
    `
    messagesParams.push(limit, offset)

    const messages = db.prepare(messagesQuery).all(...messagesParams) as Message[]

    // 2. Communication graph edges
    let graphQuery = `
      SELECT
        from_agent, to_agent,
        COUNT(*) as message_count,
        MAX(created_at) as last_message_at
      FROM messages
      WHERE workspace_id = ?
        AND ${commsPredicate}
        AND to_agent IS NOT NULL
        AND lower(from_agent) NOT IN (${humanPlaceholders})
        AND lower(to_agent) NOT IN (${humanPlaceholders})
    `
    const graphParams: any[] = [workspaceId, ...humanNames, ...humanNames]
    if (since) {
      graphQuery += " AND created_at > ?"
      graphParams.push(parseInt(since, 10))
    }
    graphQuery += " GROUP BY from_agent, to_agent ORDER BY message_count DESC"

    const edges = db.prepare(graphQuery).all(...graphParams)

    // 3. Per-agent sent/received stats
    const statsQuery = `
      SELECT agent, SUM(sent) as sent, SUM(received) as received FROM (
        SELECT from_agent as agent, COUNT(*) as sent, 0 as received
        FROM messages WHERE workspace_id = ?
          AND ${commsPredicate}
          AND to_agent IS NOT NULL
          AND lower(from_agent) NOT IN (${humanPlaceholders})
          AND lower(to_agent) NOT IN (${humanPlaceholders})
        GROUP BY from_agent
        UNION ALL
        SELECT to_agent as agent, 0 as sent, COUNT(*) as received
        FROM messages WHERE workspace_id = ?
          AND ${commsPredicate}
          AND to_agent IS NOT NULL
          AND lower(from_agent) NOT IN (${humanPlaceholders})
          AND lower(to_agent) NOT IN (${humanPlaceholders})
        GROUP BY to_agent
      ) GROUP BY agent ORDER BY (sent + received) DESC
    `
    const statsParams = [workspaceId, ...humanNames, ...humanNames, workspaceId, ...humanNames, ...humanNames]
    const agentStats = db.prepare(statsQuery).all(...statsParams)

    // 4. Total count
    let countQuery = `
      SELECT COUNT(*) as total FROM messages
      WHERE workspace_id = ?
        AND ${commsPredicate}
    `
    const countParams: any[] = [workspaceId]
    if (since) {
      countQuery += " AND created_at > ?"
      countParams.push(parseInt(since, 10))
    }
    if (agent) {
      countQuery += " AND (from_agent = ? OR to_agent = ?)"
      countParams.push(agent, agent)
    }
    const { total } = db.prepare(countQuery).get(...countParams) as { total: number }

    let seededCountQuery = `
      SELECT COUNT(*) as seeded FROM messages
      WHERE workspace_id = ?
        AND ${commsPredicate}
        AND conversation_id LIKE ?
    `
    const seededParams: any[] = [workspaceId, "conv-multi-%"]
    if (since) {
      seededCountQuery += " AND created_at > ?"
      seededParams.push(parseInt(since, 10))
    }
    if (agent) {
      seededCountQuery += " AND (from_agent = ? OR to_agent = ?)"
      seededParams.push(agent, agent)
    }
    const { seeded } = db.prepare(seededCountQuery).get(...seededParams) as { seeded: number }

    const seededCount = seeded || 0
    const liveCount = Math.max(0, total - seededCount)
    const source =
      total === 0 ? "empty" :
      liveCount === 0 ? "seeded" :
      seededCount === 0 ? "live" :
      "mixed"

    const parsed = messages.map((msg) => {
      let parsedMetadata: any = null
      if (msg.metadata) {
        try {
          parsedMetadata = JSON.parse(msg.metadata)
        } catch {
          parsedMetadata = null
        }
      }
      return {
        ...msg,
        metadata: parsedMetadata,
      }
    })

    return NextResponse.json({
      messages: parsed,
      total,
      graph: { edges, agentStats },
      source: { mode: source, seededCount, liveCount },
    })
  } catch (error) {
    logger.error({ err: error }, "GET /api/agents/comms error")
    return NextResponse.json({ error: "Failed to fetch agent communications" }, { status: 500 })
  }
}

/**
 * POST /api/agents/comms - Send an inter-agent message
 * Body: { from, to, content, topic?, message_type?, metadata? }
 * Used by agents to communicate with each other autonomously.
 */
export async function POST(request: NextRequest) {
  const auth = requireRole(request, 'operator')
  if ('error' in auth) return NextResponse.json({ error: auth.error }, { status: auth.status })

  try {
    const db = getDatabase()
    const workspaceId = auth.user.workspace_id ?? 1
    const body = await request.json()

    const from = (body.from || '').trim()
    const to = (body.to || '').trim()
    const content = (body.content || '').trim()
    const topic = (body.topic || '').trim() || null
    const message_type = body.message_type || 'text'
    const metadata = body.metadata || null

    if (!from) {
      return NextResponse.json({ error: '"from" agent name is required' }, { status: 400 })
    }
    if (!content) {
      return NextResponse.json({ error: '"content" is required' }, { status: 400 })
    }

    // Generate conversation_id for agent pair (sorted for consistency)
    const isBroadcast = !to || to === 'all'
    const conversationId = isBroadcast
      ? `a2a:broadcast:${from}:${Date.now()}`
      : `a2a:${[from, to].sort().join(':')}`

    // Upsert agent_conversations tracking
    if (!isBroadcast) {
      const existing = db
        .prepare('SELECT id, message_count FROM agent_conversations WHERE conversation_id = ? AND workspace_id = ?')
        .get(conversationId, workspaceId) as { id: number; message_count: number } | undefined

      if (existing) {
        db.prepare(`
          UPDATE agent_conversations
          SET message_count = message_count + 1, last_message_at = unixepoch(), topic = COALESCE(?, topic)
          WHERE id = ?
        `).run(topic, existing.id)
      } else {
        db.prepare(`
          INSERT INTO agent_conversations (conversation_id, agent_a, agent_b, topic, message_count, last_message_at, workspace_id)
          VALUES (?, ?, ?, ?, 1, unixepoch(), ?)
        `).run(conversationId, from, to, topic, workspaceId)
      }
    }

    // Insert message
    const stmt = db.prepare(`
      INSERT INTO messages (conversation_id, from_agent, to_agent, content, message_type, metadata, workspace_id)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `)

    if (isBroadcast) {
      // Send to all known agents
      const agents = db
        .prepare('SELECT name FROM agents WHERE workspace_id = ? AND status != ?')
        .all(workspaceId, 'offline') as { name: string }[]

      const recipients = agents.filter(a => a.name.toLowerCase() !== from.toLowerCase())
      const messageIds: number[] = []

      for (const agent of recipients) {
        const result = stmt.run(
          conversationId,
          from,
          agent.name,
          content,
          message_type,
          metadata ? JSON.stringify(metadata) : null,
          workspaceId
        )
        messageIds.push(result.lastInsertRowid as number)

        // Create notification for each recipient
        db_helpers.createNotification(
          agent.name,
          'agent_broadcast',
          `Broadcast from ${from}`,
          content.substring(0, 200),
          'message',
          result.lastInsertRowid as number,
          workspaceId
        )
      }

      // Log activity
      db_helpers.logActivity(
        'agent_broadcast',
        'message',
        messageIds[0] || 0,
        from,
        `Broadcast to ${recipients.length} agents: ${content.substring(0, 100)}`,
        { topic, recipients: recipients.map(r => r.name) },
        workspaceId
      )

      // Broadcast to SSE
      eventBus.broadcast('chat.message', {
        conversation_id: conversationId,
        from_agent: from,
        to_agent: 'all',
        content,
        message_type,
        type: 'broadcast',
        recipient_count: recipients.length,
      })

      return NextResponse.json({
        sent: true,
        broadcast: true,
        recipients: recipients.map(r => r.name),
        conversation_id: conversationId,
      }, { status: 201 })
    } else {
      // Direct agent-to-agent message
      const result = stmt.run(
        conversationId,
        from,
        to,
        content,
        message_type,
        metadata ? JSON.stringify(metadata) : null,
        workspaceId
      )

      const messageId = result.lastInsertRowid as number
      const created = db.prepare('SELECT * FROM messages WHERE id = ? AND workspace_id = ?').get(messageId, workspaceId) as Message

      // Notification
      db_helpers.createNotification(
        to,
        'agent_message',
        `Message from ${from}`,
        content.substring(0, 200),
        'message',
        messageId,
        workspaceId
      )

      // Activity log
      db_helpers.logActivity(
        'agent_comms',
        'message',
        messageId,
        from,
        `Sent message to ${to}: ${content.substring(0, 100)}`,
        { topic, conversation_id: conversationId },
        workspaceId
      )

      // SSE broadcast
      eventBus.broadcast('chat.message', {
        ...created,
        metadata: metadata || null,
      })

      return NextResponse.json({
        sent: true,
        message_id: messageId,
        conversation_id: conversationId,
      }, { status: 201 })
    }
  } catch (error) {
    logger.error({ err: error }, "POST /api/agents/comms error")
    return NextResponse.json({ error: "Failed to send inter-agent message" }, { status: 500 })
  }
}
