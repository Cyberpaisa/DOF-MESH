import { NextRequest, NextResponse } from "next/server"
import { getDatabase, db_helpers } from "@/lib/db"
import { requireRole } from '@/lib/auth'
import { logger } from '@/lib/logger'
import { eventBus } from '@/lib/event-bus'

/**
 * POST /api/agents/comms/broadcast - Broadcast a message to all agents
 * Body: { from, content, topic?, message_type?, metadata?, priority? }
 * Used for system announcements, discovery sharing, brainstorming calls.
 */
export async function POST(request: NextRequest) {
  const auth = requireRole(request, 'operator')
  if ('error' in auth) return NextResponse.json({ error: auth.error }, { status: auth.status })

  try {
    const db = getDatabase()
    const workspaceId = auth.user.workspace_id ?? 1
    const body = await request.json()

    const from = (body.from || '').trim()
    const content = (body.content || '').trim()
    const topic = (body.topic || '').trim() || null
    const message_type = body.message_type || 'text'
    const metadata = body.metadata || null
    const priority = body.priority || 'normal'

    if (!from) {
      return NextResponse.json({ error: '"from" agent name is required' }, { status: 400 })
    }
    if (!content) {
      return NextResponse.json({ error: '"content" is required' }, { status: 400 })
    }

    const conversationId = `a2a:broadcast:${from}:${Date.now()}`

    // Get all agents except sender
    const agents = db
      .prepare('SELECT name FROM agents WHERE workspace_id = ? AND name != ?')
      .all(workspaceId, from) as { name: string }[]

    if (agents.length === 0) {
      return NextResponse.json({ error: 'No agents available to broadcast to' }, { status: 404 })
    }

    const stmt = db.prepare(`
      INSERT INTO messages (conversation_id, from_agent, to_agent, content, message_type, metadata, workspace_id)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `)

    const metaJson = JSON.stringify({
      ...(metadata || {}),
      broadcast: true,
      topic,
      priority,
      recipient_count: agents.length,
    })

    const messageIds: number[] = []

    db.transaction(() => {
      for (const agent of agents) {
        const result = stmt.run(
          conversationId,
          from,
          agent.name,
          content,
          message_type,
          metaJson,
          workspaceId
        )
        messageIds.push(result.lastInsertRowid as number)

        db_helpers.createNotification(
          agent.name,
          priority === 'urgent' ? 'urgent_broadcast' : 'agent_broadcast',
          `${priority === 'urgent' ? '🚨 ' : ''}Broadcast from ${from}${topic ? `: ${topic}` : ''}`,
          content.substring(0, 200),
          'message',
          result.lastInsertRowid as number,
          workspaceId
        )
      }
    })()

    // Activity log
    db_helpers.logActivity(
      'agent_broadcast',
      'message',
      messageIds[0] || 0,
      from,
      `Broadcast [${priority}] to ${agents.length} agents${topic ? ` re: ${topic}` : ''}: ${content.substring(0, 100)}`,
      { topic, priority, recipients: agents.map(a => a.name), conversation_id: conversationId },
      workspaceId
    )

    // SSE
    eventBus.broadcast('chat.message', {
      conversation_id: conversationId,
      from_agent: from,
      to_agent: 'all',
      content,
      message_type: 'broadcast',
      metadata: { topic, priority, recipient_count: agents.length },
    })

    return NextResponse.json({
      sent: true,
      broadcast: true,
      conversation_id: conversationId,
      recipients: agents.map(a => a.name),
      message_ids: messageIds,
    }, { status: 201 })
  } catch (error) {
    logger.error({ err: error }, "POST /api/agents/comms/broadcast error")
    return NextResponse.json({ error: "Failed to broadcast message" }, { status: 500 })
  }
}
