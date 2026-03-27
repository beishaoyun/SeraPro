import { useEffect, useRef, useCallback } from 'react'

export interface WebSocketMessage {
  type: 'deployment_update' | 'step_log' | 'deployment_complete'
  deployment_id: number
  data?: {
    status?: string
    current_step?: number
    total_steps?: number
  }
  step_number?: number
  log?: {
    step_number: number
    description: string
    command?: string
    status: string
    output?: string
    error_message?: string
    duration_ms?: number
  }
  success?: boolean
  error_message?: string
}

export interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useDeploymentWebSocket(
  deploymentId: number | null,
  options: UseWebSocketOptions = {}
) {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!deploymentId) return

    // 创建 WebSocket 连接
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/deployments/ws/${deploymentId}`

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      reconnectAttemptsRef.current = 0
      onConnect?.()
    }

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        console.log('WebSocket message:', message)
        onMessage?.(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket closed')
      onDisconnect?.()

      // 尝试重连
      if (reconnectAttemptsRef.current < maxReconnectAttempts && deploymentId) {
        reconnectAttemptsRef.current += 1
        console.log(`Reconnecting in ${reconnectInterval}ms (attempt ${reconnectAttemptsRef.current})`)

        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, reconnectInterval)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    wsRef.current = ws
  }, [deploymentId, onMessage, onConnect, onDisconnect, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const sendMessage = useCallback((data: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(data)
    }
  }, [])

  useEffect(() => {
    if (deploymentId) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [deploymentId, connect, disconnect])

  return {
    connect,
    disconnect,
    sendMessage,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  }
}
