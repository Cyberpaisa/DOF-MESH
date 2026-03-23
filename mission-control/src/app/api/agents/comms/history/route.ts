import { NextRequest, NextResponse } from "next/server"
import { getDatabase } from "@/lib/db"
import { requireRole } from '@/lib/auth'
import { logger } from '@/lib/logger'

/**
 * GET /api/agents/comms/history - Browse historical inter-agent conversations
 * Query params:
 *   agent_a, agent_b — filter by agent pair
 *   topic — filter by topic
 *   status — active | archived (default: all)
 *   limit, offset — pagination
 *   date_from, date_to — date range (unix timestamps)
 */
export async function GET(request: NextRequest) {
  const auth = requireRole(request, 'viewer')
  if ('error' in auth) return NextResponse.json({ error: auth.error }, { status: auth.status })

  try {
    const db = getDatabase()
    const workspaceId = auth.user.workspace_id ?? 1
    const { searchParams } = new URL(request.url)

    const agent_a = searchParams.get("agent_a")
    const agent_b = searchParams.get("agent_b")
    const topic = searchParams.get("topic")
    const status = searchParams.get("status")
    const date_from = searchParams.get("date_from")
    const date_to = searchParams.get("date_to")
    const limit = Math.min(parseInt(searchParams.get("limit") || "50"), 200)
    const offset = parseInt(searchParams.get("offset") || "0")

    // Check if agent_conversations table exists
    const tableExists = db
      .prepare(`SELECT 1 as ok FROM sqlite_master WHERE type = 'table' AND name = 'agent_conversations'`)
      .get() as { ok?: number } | undefined

    if (!tableExists?.ok) {
      // Fallback: derive conversations from messages table
      let query = `
        SELECT
          conversation_id,
          MIN(from_agent) as agent_a,
          MIN(to_agent) as agent_b,
          COUNT(*) as message_count,
          MAX(created_at) as last_message_at,
          MIN(created_at) as created_at
        FROM messages
        WHERE workspace_id = ?
          AND conversation_id LIKE 'a2a:%'
      `
      const params: any[] = [workspaceId]

      if (agent_a) {
        query += " AND (from_agent = ? OR to_agent = ?)"
        params.push(agent_a, agent_a)
      }
      if (agent_b) {
        query += " AND (from_agent = ? OR to_agent = ?)"
        params.push(agent_b, agent_b)
      }
      if (date_from) {
        query += " AND created_at >= ?"
        params.push(parseInt(date_from))
      }
      if (date_to) {
        query += " AND created_at <= ?"
        params.push(parseInt(date_to))
      }

      query += " GROUP BY conversation_id ORDER BY last_message_at DESC LIMIT ? OFFSET ?"
      params.push(limit, offset)

      const conversations = db.prepare(query).all(...params)
      return NextResponse.json({ conversations, total: conversations.length })
    }

    // Use agent_conversations table
    let query = "SELECT * FROM agent_conversations WHERE workspace_id = ?"
    const params: any[] = [workspaceId]

    if (agent_a) {
      query += " AND (agent_a = ? OR agent_b = ?)"
      params.push(agent_a, agent_a)
    }
    if (agent_b) {
      query += " AND (agent_a = ? OR agent_b = ?)"
      params.push(agent_b, agent_b)
    }
    if (topic) {
      query += " AND topic LIKE ?"
      params.push(`%${topic}%`)
    }
    if (status) {
      query += " AND status = ?"
      params.push(status)
    }
    if (date_from) {
      query += " AND created_at >= ?"
      params.push(parseInt(date_from))
    }
    if (date_to) {
      query += " AND created_at <= ?"
      params.push(parseInt(date_to))
    }

    // Count total
    const countQuery = query.replace("SELECT *", "SELECT COUNT(*) as total")
    const { total } = db.prepare(countQuery).get(...params) as { total: number }

    query += " ORDER BY last_message_at DESC LIMIT ? OFFSET ?"
    params.push(limit, offset)

    const conversations = db.prepare(query).all(...params)

    // For each conversation, get the last message preview
    const enriched = conversations.map((conv: any) => {
      const lastMsg = db
        .prepare(`
          SELECT from_agent, content, message_type, created_at
          FROM messages
          WHERE conversation_id = ? AND workspace_id = ?
          ORDER BY created_at DESC
          LIMIT 1
        `)
        .get(conv.conversation_id, workspaceId) as any

      return {
        ...conv,
        last_message: lastMsg ? {
          from: lastMsg.from_agent,
          preview: lastMsg.content.substring(0, 150),
          type: lastMsg.message_type,
          at: lastMsg.created_at,
        } : null,
      }
    })

    return NextResponse.json({ conversations: enriched, total })
  } catch (error) {
    logger.error({ err: error }, "GET /api/agents/comms/history error")
    return NextResponse.json({ error: "Failed to fetch conversation history" }, { status: 500 })
  }
}
