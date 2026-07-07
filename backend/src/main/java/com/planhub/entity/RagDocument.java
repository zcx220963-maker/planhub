package com.planhub.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * RAG 知识库文档元数据
 * <p>
 * 存储上传到 RAG 知识库的文档信息，
 * 实际的向量存储在 Python 端的 Chroma 中，
 * 关键词索引在 rag_bm25_index 表中。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("rag_documents")
public class RagDocument {

    @TableId
    private String id;

    /** 所属用户ID */
    @TableField("user_id")
    private Long userId;

    /** 原始文件名 */
    @TableField("filename")
    private String filename;

    /** 文件大小（字节） */
    @TableField("file_size")
    private Long fileSize;

    /** 切分片段数 */
    @TableField("chunk_count")
    private Integer chunkCount;

    /** 磁盘文件路径（兼容旧逻辑） */
    @TableField("file_path")
    private String filePath;

    /** 状态: active/deleted */
    @TableField("status")
    private String status;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;

    @TableField("deleted_at")
    private LocalDateTime deletedAt;
}
