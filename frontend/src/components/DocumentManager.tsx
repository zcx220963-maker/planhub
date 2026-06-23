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

import React from 'react';
import { Upload, FileText, Trash2, Loader2 } from 'lucide-react';

interface Document {
    id: number;
    name: string;
    content?: string;
}

interface DocumentManagerProps {
    documents: Document[];
    selectedDocIds: number[];
    onUpload: (files: FileList) => Promise<void>;
    onDelete: (docId: number) => Promise<void>;
    onToggleSelection: (docId: number) => void;
    onToggleAll: () => void;
    isUploading?: boolean;
}

const DocumentManager: React.FC<DocumentManagerProps> = ({
    documents,
    selectedDocIds,
    onUpload,
    onDelete,
    onToggleSelection,
    onToggleAll,
    isUploading = false,
}) => {
    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            await onUpload(files);
            e.target.value = ''; // 重置 input
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
                                    background: selectedDocIds.includes(doc.id) ? '#f1f5f9' : 'white',
                                    borderRadius: '8px',
                                    marginBottom: '8px',
                                    border: '1px solid',
                                    borderColor: selectedDocIds.includes(doc.id) ? '#667eea' : '#e2e8f0',
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
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        overflow: 'hidden',
                                    }}>
                                        <FileText size={16} style={{ color: '#64748b', flexShrink: 0 }} />
                                        <span style={{
                                            fontSize: '13px',
                                            color: '#334155',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                        }}>
                                            {doc.name}
                                        </span>
                                    </div>
                                </label>
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
        </div>
    );
};

export default DocumentManager;
