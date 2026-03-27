"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建枚举类型
    sa.Enum('user', 'admin', name='userrole').create(op.get_bind())
    sa.Enum('active', 'inactive', 'error', name='serverstatus').create(op.get_bind())
    sa.Enum('pending', 'running', 'success', 'failed', 'cancelled', name='deploymentstatus').create(op.get_bind())

    # 用户表
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('user', 'admin', name='userrole', create_type=False), nullable=True),
        sa.Column('is_disabled', sa.Boolean(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 服务器表
    op.create_table('servers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('auth_type', sa.String(length=50), nullable=False),
        sa.Column('credentials', sa.Text(), nullable=False),
        sa.Column('os_type', sa.String(length=50), nullable=False),
        sa.Column('os_version', sa.String(length=50), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'inactive', 'error', name='serverstatus', create_type=False), nullable=True),
        sa.Column('last_connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_servers_id'), 'servers', ['id'], unique=False)
    op.create_index(op.f('ix_servers_user_id'), 'servers', ['user_id'], unique=False)

    # 部署表
    op.create_table('deployments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('github_url', sa.String(length=500), nullable=False),
        sa.Column('github_repo_name', sa.String(length=255), nullable=True),
        sa.Column('service_type', sa.String(length=50), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'running', 'success', 'failed', 'cancelled', name='deploymentstatus', create_type=False), nullable=True),
        sa.Column('current_step', sa.Integer(), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deployments_id'), 'deployments', ['id'], unique=False)
    op.create_index(op.f('ix_deployments_user_id'), 'deployments', ['user_id'], unique=False)
    op.create_index(op.f('ix_deployments_server_id'), 'deployments', ['server_id'], unique=False)

    # 部署步骤表
    op.create_table('deployment_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('deployment_id', sa.Integer(), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('command', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deployment_steps_id'), 'deployment_steps', ['id'], unique=False)
    op.create_index(op.f('ix_deployment_steps_deployment_id'), 'deployment_steps', ['deployment_id'], unique=False)

    # 知识库表
    op.create_table('knowledge_base',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_url_hash', sa.String(length=64), nullable=False),
        sa.Column('github_url', sa.Text(), nullable=False),
        sa.Column('os_type', sa.String(length=50), nullable=False),
        sa.Column('os_version', sa.String(length=50), nullable=False),
        sa.Column('service_type', sa.String(length=50), nullable=False),
        sa.Column('deploy_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('common_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('success_count', sa.Integer(), nullable=True),
        sa.Column('failure_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('github_url_hash')
    )
    op.create_index(op.f('ix_knowledge_base_id'), 'knowledge_base', ['id'], unique=False)

    # 审计日志表
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)

    # AI 成本记录表
    op.create_table('ai_cost_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('deployment_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_cny', sa.Float(), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_cost_records_id'), 'ai_cost_records', ['id'], unique=False)
    op.create_index(op.f('ix_ai_cost_records_created_at'), 'ai_cost_records', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('ai_cost_records')
    op.drop_table('audit_logs')
    op.drop_table('knowledge_base')
    op.drop_table('deployment_steps')
    op.drop_table('deployments')
    op.drop_table('servers')
    op.drop_table('users')

    # 删除枚举类型
    sa.Enum(name='deploymentstatus').drop(op.get_bind())
    sa.Enum(name='serverstatus').drop(op.get_bind())
    sa.Enum(name='userrole').drop(op.get_bind())
