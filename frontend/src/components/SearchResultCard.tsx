/**
 * 搜索结果卡片组件
 *
 * 展示搜索结果，并提供一键跳转按钮
 * 不需要AI参与跳转逻辑，用户点击即可跳转
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, MessageSquare } from 'lucide-react';

interface SearchResult {
    display_id: number;
    real_id: number;
    title?: string;
    content?: string;
    type: 'plan' | 'post';
}

interface SearchResultCardProps {
    results: {
        plans?: SearchResult[];
        posts?: SearchResult[];
    };
    onJump?: (type: 'plan' | 'post', id: number) => void;
}

const SearchResultCard: React.FC<SearchResultCardProps> = ({ results, onJump }) => {
    const navigate = useNavigate();

    const handleJump = (type: 'plan' | 'post', id: number) => {
        if (onJump) {
            onJump(type, id);
        } else {
            // 直接跳转，不需要调用AI
            const path = type === 'plan' ? `/plan/${id}` : `/post/${id}`;
            navigate(path);
        }
    };

    const plans = results.plans || [];
    const posts = results.posts || [];

    if (plans.length === 0 && posts.length === 0) {
        return null;
    }

    return (
        <div style={{
            background: '#f8fafc',
            borderRadius: '12px',
            padding: '16px',
            marginTop: '12px',
            border: '1px solid #e2e8f0',
        }}>
            <div style={{
                fontSize: '14px',
                fontWeight: 600,
                color: '#475569',
                marginBottom: '12px',
            }}>
                搜索结果
            </div>

            {/* 计划列表 */}
            {plans.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                    <div style={{
                        fontSize: '12px',
                        color: '#64748b',
                        marginBottom: '8px',
                        fontWeight: 500,
                    }}>
                        计划 ({plans.length})
                    </div>
                    {plans.map((plan) => (
                        <div
                            key={`plan-${plan.display_id}`}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                padding: '10px 12px',
                                background: 'white',
                                borderRadius: '8px',
                                marginBottom: '8px',
                                border: '1px solid #e2e8f0',
                                transition: 'all 0.2s',
                                cursor: 'pointer',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = '#667eea';
                                e.currentTarget.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.1)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = '#e2e8f0';
                                e.currentTarget.style.boxShadow = 'none';
                            }}
                            onClick={() => handleJump('plan', plan.real_id)}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <div style={{
                                    width: '28px',
                                    height: '28px',
                                    borderRadius: '6px',
                                    background: '#667eea',
                                    color: 'white',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '12px',
                                    fontWeight: 600,
                                }}>
                                    {plan.display_id}
                                </div>
                                <div>
                                    <div style={{
                                        fontSize: '14px',
                                        fontWeight: 500,
                                        color: '#1e293b',
                                    }}>
                                        {plan.title || '无标题'}
                                    </div>
                                    <div style={{
                                        fontSize: '12px',
                                        color: '#64748b',
                                    }}>
                                        ID: {plan.real_id}
                                    </div>
                                </div>
                            </div>
                            <button
                                style={{
                                    padding: '6px 12px',
                                    background: '#667eea',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '12px',
                                    fontWeight: 500,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleJump('plan', plan.real_id);
                                }}
                            >
                                <FileText size={14} />
                                查看详情
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* 帖子列表 */}
            {posts.length > 0 && (
                <div>
                    <div style={{
                        fontSize: '12px',
                        color: '#64748b',
                        marginBottom: '8px',
                        fontWeight: 500,
                    }}>
                        帖子 ({posts.length})
                    </div>
                    {posts.map((post) => (
                        <div
                            key={`post-${post.display_id}`}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                padding: '10px 12px',
                                background: 'white',
                                borderRadius: '8px',
                                marginBottom: '8px',
                                border: '1px solid #e2e8f0',
                                transition: 'all 0.2s',
                                cursor: 'pointer',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = '#667eea';
                                e.currentTarget.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.1)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = '#e2e8f0';
                                e.currentTarget.style.boxShadow = 'none';
                            }}
                            onClick={() => handleJump('post', post.real_id)}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <div style={{
                                    width: '28px',
                                    height: '28px',
                                    borderRadius: '6px',
                                    background: '#10b981',
                                    color: 'white',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '12px',
                                    fontWeight: 600,
                                }}>
                                    {post.display_id}
                                </div>
                                <div style={{ flex: 1 }}>
                                    <div style={{
                                        fontSize: '14px',
                                        color: '#1e293b',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap',
                                        maxWidth: '300px',
                                    }}>
                                        {post.content || '无内容'}
                                    </div>
                                    <div style={{
                                        fontSize: '12px',
                                        color: '#64748b',
                                    }}>
                                        ID: {post.real_id}
                                    </div>
                                </div>
                            </div>
                            <button
                                style={{
                                    padding: '6px 12px',
                                    background: '#10b981',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '12px',
                                    fontWeight: 500,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleJump('post', post.real_id);
                                }}
                            >
                                <MessageSquare size={14} />
                                查看详情
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* 提示信息 */}
            <div style={{
                fontSize: '12px',
                color: '#94a3b8',
                marginTop: '8px',
                textAlign: 'center',
            }}>
                点击卡片或按钮即可查看详情
            </div>
        </div>
    );
};

export default SearchResultCard;
