"""add_system_config_table

Revision ID: c44a5c0e54d6
Revises: 001_initial
Create Date: 2026-03-28 14:34:10.103300

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c44a5c0e54d6'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'system_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )
    op.create_index(op.f('ix_system_config_config_key'), 'system_config', ['config_key'], unique=False)
    op.create_index(op.f('ix_system_config_id'), 'system_config', ['id'], unique=False)

    # 插入默认配置
    op.bulk_insert(
        sa.table('system_config',
            sa.column('config_key', sa.String()),
            sa.column('config_value', sa.String()),
            sa.column('description', sa.String()),
        ),
        [
            {'config_key': 'openai_api_key', 'config_value': '', 'description': 'OpenAI API Key'},
            {'config_key': 'openai_enabled', 'config_value': 'true', 'description': 'OpenAI 是否启用'},
            {'config_key': 'openai_model', 'config_value': 'gpt-4o-mini', 'description': 'OpenAI 模型'},

            {'config_key': 'volcengine_api_key', 'config_value': '', 'description': '火山引擎 API Key'},
            {'config_key': 'volcengine_enabled', 'config_value': 'true', 'description': '火山引擎是否启用'},
            {'config_key': 'volcengine_model', 'config_value': 'doubao-pro-32k', 'description': '火山引擎模型'},

            {'config_key': 'alibaba_api_key', 'config_value': '', 'description': '阿里云 API Key'},
            {'config_key': 'alibaba_enabled', 'config_value': 'true', 'description': '阿里云是否启用'},
            {'config_key': 'alibaba_model', 'config_value': 'qwen-plus', 'description': '阿里云模型'},

            {'config_key': 'deepseek_api_key', 'config_value': '', 'description': 'DeepSeek API Key'},
            {'config_key': 'deepseek_enabled', 'config_value': 'true', 'description': 'DeepSeek 是否启用'},
            {'config_key': 'deepseek_model', 'config_value': 'deepseek-chat', 'description': 'DeepSeek 模型'},

            {'config_key': 'ai_provider', 'config_value': 'auto', 'description': 'AI Provider 选择'},
            {'config_key': 'default_model', 'config_value': 'doubao-pro-32k', 'description': '默认模型'},

            {'config_key': 'max_servers_per_user', 'config_value': '10', 'description': '每用户最大服务器数'},
            {'config_key': 'max_deployments_per_day', 'config_value': '50', 'description': '每用户每日最大部署数'},
            {'config_key': 'enable_registration', 'config_value': 'true', 'description': '是否开放注册'},
            {'config_key': 'enable_ai_debug', 'config_value': 'true', 'description': '是否启用 AI 排错'},
            {'config_key': 'free_tier_ai_budget_cny', 'config_value': '10.0', 'description': '免费用户 AI 预算'},
        ]
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_system_config_id'), table_name='system_config')
    op.drop_index(op.f('ix_system_config_config_key'), table_name='system_config')
    op.drop_table('system_config')
