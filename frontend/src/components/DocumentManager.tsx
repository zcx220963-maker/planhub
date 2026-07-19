/**
 * 文档管理组件
 *
 * 从 RAG.tsx 提取的文档管理功能，可复用于 ChatBot 页面
 * 功能：
 * - 文档上传
 * - 文档列表显示
 * - 文档选择（用于指定知识库查询）
 * - 文档删除
 */

import React, { useState } from 'react';
import { Upload, FileText, Trash2, Loader2, X, BookOpen } from 'lucide-react';
import { planAssistantApi } from '../services/api';

interface Document {
    id: string;
    name: string;
    content?: string;
}

interface DocumentManagerProps {
    documents: Document[];
    selectedDocIds: string[];
    onUpload: (files: FileList) => Promise<void>;
    onDelete: (docId: string) => Promise<void>;
    onToggleSelection: (docId: string) => void;
    onToggleAll: () => void;
    isUploading?: boolean;
    userId?: string;
}

const DocumentManager: React.FC<DocumentManagerProps> = ({
    documents,
    selectedDocIds,
    onUpload,
    onDelete,
    onToggleSelection,
    onToggleAll,
    isUploading = false,
    userId = 'standalone_user',
}) => {
    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            await onUpload(files);
            e.target.value = ''; // 重置 input
        }
    };

    // ── 文档预览状态 ──
    const [previewDoc, setPreviewDoc] = useState<{ id: string; name: string; content: string; length: number } | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);

    const handlePreview = async (docId: string) => {
        setPreviewLoading(true);
        try {
            const data = await planAssistantApi.getDocumentPreview(docId, userId);
            setPreviewDoc(data);
        } catch {
            // 静默失败
        } finally {
            setPreviewLoading(false);
        }
    };

    return (
        <div style={{
            width: '350px',
            background: 'white',
            borderLeft: '1px solid #e2e8f0',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            position: 'relative',
        }}>
            {/* 头部 */}
            <div style={{
                padding: '16px 20px',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
            }}>
                <h3 style={{
                    margin: 0,
                    fontSize: '16px',
                    fontWeight: 600,
                    color: '#0f172a',
                }}>
                    知识库文档
                </h3>
                <span style={{
                    fontSize: '12px',
                    color: '#64748b',
                }}>
                    {documents.length} 个文档
                </span>
            </div>

            {/* 上传区域 */}
            <div style={{ padding: '16px' }}>
                <label style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '20px',
                    border: '2px dashed #e2e8f0',
                    borderRadius: '8px',
                    cursor: isUploading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s',
                    opacity: isUploading ? 0.6 : 1,
                }}
                onMouseEnter={(e) => {
                    if (!isUploading) {
                        e.currentTarget.style.borderColor = '#667eea';
                        e.currentTarget.style.background = '#f8fafc';
                    }
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#e2e8f0';
                    e.currentTarget.style.background = 'transparent';
                }}
                >
                    <input
                        type="file"
                        onChange={handleFileChange}
                        style={{ display: 'none' }}
                        disabled={isUploading}
                        multiple
                        accept=".txt,.md,.pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.json,.csv"
                    />
                    {isUploading ? (
                        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: '#667eea' }} />
                    ) : (
                        <>
                            <Upload size={24} style={{ color: '#64748b', marginBottom: '8px' }} />
                            <span style={{ fontSize: '14px', color: '#333', marginBottom: '4px' }}>
                                上传文档
                            </span>
                            <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                                支持 txt/pdf/docx 等
                            </span>
                        </>
                    )}
                </label>
            </div>

            {/* 文档列表 */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '0 16px 16px',
            }}>
                {documents.length > 0 ? (
                    <>
                        {/* 全选 */}
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginBottom: '12px',
                        }}>
                            <label style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                cursor: 'pointer',
                                fontSize: '13px',
                                color: '#64748b',
                            }}>
                                <input
                                    type="checkbox"
                                    checked={selectedDocIds.length === documents.length && documents.length > 0}
                                    onChange={onToggleAll}
                                    style={{ cursor: 'pointer' }}
                                />
                                已上传文档 ({documents.length})
                            </label>
                            {selectedDocIds.length > 0 && (
                                <span style={{
                                    fontSize: '12px',
                                    color: '#667eea',
                                }}>
                                    已选 {selectedDocIds.length} 个
                                </span>
                            )}
                        </div>

                        {/* 文档项 */}
                        {documents.map((doc) => (
                            <div
                                key={doc.id}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    padding: '10px 12px',
                                    background: selectedDocIds.includes(doc.id) ? '#eef2ff' : (previewDoc?.id === doc.id) ? '#f8fafc' : 'white',
                                    borderRadius: '8px',
                                    marginBottom: '8px',
                                    border: '1px solid',
                                    borderColor: selectedDocIds.includes(doc.id) ? '#6366f1' : '#e2e8f0',
                                    transition: 'all 0.2s',
                                }}
                            >
                                <label style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    flex: 1,
                                    cursor: 'pointer',
                                    overflow: 'hidden',
                                }}>
                                    <input
                                        type="checkbox"
                                        checked={selectedDocIds.includes(doc.id)}
                                        onChange={() => onToggleSelection(doc.id)}
                                        style={{ cursor: 'pointer', flexShrink: 0 }}
                                    />
                                    <div
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            overflow: 'hidden',
                                            flex: 1,
                                        }}
                                        onClick={() => handlePreview(doc.id)}
                                        title="点击预览文档内容"
                                    >
                                        <FileText size={16} style={{ color: '#64748b', flexShrink: 0 }} />
                                        <span style={{
                                            fontSize: '13px',
                                            color: '#334155',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                            cursor: 'pointer',
                                        }}>
                                            {doc.name}
                                        </span>
                                    </div>
                                </label>
                                <button
                                    onClick={(e) => { e.stopPropagation(); handlePreview(doc.id); }}
                                    style={{
                                        background: 'none',
                                        border: 'none',
                                        color: '#94a3b8',
                                        cursor: 'pointer',
                                        padding: '4px',
                                        borderRadius: '4px',
                                        transition: 'all 0.2s',
                                        flexShrink: 0,
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.color = '#6366f1';
                                        e.currentTarget.style.background = '#eef2ff';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.color = '#94a3b8';
                                        e.currentTarget.style.background = 'none';
                                    }}
                                    title="预览文档"
                                >
                                    <BookOpen size={14} />
                                </button>
                                <button
                                    onClick={() => onDelete(doc.id)}
                                    style={{
                                        background: 'none',
                                        border: 'none',
                                        color: '#94a3b8',
                                        cursor: 'pointer',
                                        padding: '4px',
                                        borderRadius: '4px',
                                        transition: 'all 0.2s',
                                        flexShrink: 0,
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.color = '#ef4444';
                                        e.currentTarget.style.background = '#fee2e2';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.color = '#94a3b8';
                                        e.currentTarget.style.background = 'none';
                                    }}
                                    title="删除文档"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))}

                        {/* 提示 */}
                        <div style={{
                            fontSize: '12px',
                            color: '#64748b',
                            marginTop: '12px',
                            padding: '8px 12px',
                            background: '#f8fafc',
                            borderRadius: '6px',
                        }}>
                            {selectedDocIds.length > 0 ? (
                                <>已选择 {selectedDocIds.length} 个文档，AI 将基于选中的文档回答</>
                            ) : (
                                <>选择文档后，AI 将只基于选中的文档进行回答</>
                            )}
                        </div>
                    </>
                ) : (
                    <div style={{
                        textAlign: 'center',
                        padding: '40px 20px',
                        color: '#94a3b8',
                        fontSize: '14px',
                    }}>
                        暂无已上传文档
                        <br />
                        <span style={{ fontSize: '12px' }}>
                            上传文档后即可使用知识库功能
                        </span>
                    </div>
                )}
            </div>

            {/* ── 文档预览面板 ── */}
            {previewDoc && (
                <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'white',
                    display: 'flex',
                    flexDirection: 'column',
                    zIndex: 10,
                }}>
                    {/* 预览头部 */}
                    <div style={{
                        padding: '14px 16px',
                        borderBottom: '1px solid #e5e7eb',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: '#faf9f6',
                        flexShrink: 0,
                    }}>
                        <div style={{ flex: 1, minWidth: 0, marginRight: 8 }}>
                            <div style={{
                                fontSize: '14px',
                                fontWeight: 600,
                                color: '#1a1a2e',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                            }}>
                                {previewDoc.name}
                            </div>
                            <div style={{
                                fontSize: '11px',
                                color: '#94a3b8',
                                marginTop: 2,
                            }}>
                                {previewDoc.length.toLocaleString()} 字符
                            </div>
                        </div>
                        <button
                            onClick={() => setPreviewDoc(null)}
                            style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                color: '#94a3b8',
                                padding: 6,
                                borderRadius: 6,
                                display: 'flex',
                                alignItems: 'center',
                                flexShrink: 0,
                            }}
                            title="关闭预览"
                        >
                            <X size={16} />
                        </button>
                    </div>
                    {/* 预览内容 */}
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '20px 24px',
                        background: '#faf9f6',
                    }}>
                        {previewLoading ? (
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                height: '100%',
                                color: '#94a3b8',
                                fontSize: 13,
                            }}>
                                <Loader2 size={18} style={{ animation: 'spin 1s linear infinite', marginRight: 8 }} />
                                加载中...
                            </div>
                        ) : (
                            <pre style={{
                                fontFamily: "'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif",
                                fontSize: 14,
                                lineHeight: 1.8,
                                color: '#374151',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                margin: 0,
                            }}>
                                {previewDoc.content}
                            </pre>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default DocumentManager;
