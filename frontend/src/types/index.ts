// API 响应类型定义

export interface User {
  id: number
  email: string
  role: 'user' | 'admin'
  created_at: string
  last_login_at?: string
  is_disabled: boolean
}

export interface Server {
  id: number
  name: string
  host: string
  port: number
  username?: string
  os_type: string
  os_version: string
  status: 'active' | 'inactive' | 'error'
  created_at: string
  updated_at: string
}

export interface Deployment {
  id: number
  user_id: number
  server_id: number
  github_url: string
  github_repo_name?: string
  service_type?: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
  current_step: number
  total_steps: number
  error_log?: string
  created_at: string
  updated_at: string
}

export interface DeploymentStep {
  id: number
  deployment_id: number
  step_number: number
  description: string
  command?: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  output?: string
  error_message?: string
  duration_ms?: number
  created_at: string
}

export interface DeploymentWithSteps extends Deployment {
  steps: DeploymentStep[]
}

export interface KnowledgeItem {
  id: number
  github_url: string
  os_type: string
  os_version: string
  service_type: string
  deploy_steps: Array<{ step: number; description: string; command: string }>
  common_errors: Array<{ step: number; error: string }>
  success_count: number
  failure_count: number
  created_at: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  company?: string
}

export interface ServerCreate {
  name: string
  host: string
  port?: number
  username?: string
  password?: string
  ssh_key?: string
  os_type: string
  os_version: string
}

export interface DeploymentCreate {
  server_id: number
  github_url: string
  service_type?: string
}

export interface ErrorReport {
  id: number
  error_type: string
  error_level: 'info' | 'warning' | 'error' | 'critical'
  category: 'system' | 'deployment' | 'ai' | 'security'
  message: string
  count: number
  last_occurred: string
}

export interface SystemStats {
  total_users: number
  total_servers: number
  total_deployments: number
  successful_deployments: number
  failed_deployments: number
  ai_calls_today: number
  ai_cost_today: number
}
