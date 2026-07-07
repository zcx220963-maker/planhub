package com.planhub.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * RAG BM25 倒排索引
 * <p>
 * 每个词一行：(doc_id, chunk_index, term) -> tf
 * 用于支持基于关键词的 BM25 检索。
 * <p>
 * 检索时：
 * 1. 把用户查询分词
 * 2. 用 WHERE term IN (...) 一次查出所有命中的 chunk
 * 3. 在内存中按 BM25 公式计算分数
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("rag_bm25_index")
public class RagBm25Index {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 文档ID（关联 rag_documents.id） */
    @TableField("doc_id")
    private String docId;

    /** 片段序号（文档切分后的第 N 块） */
    @TableField("chunk_index")
    private Integer chunkIndex;

    /** 分词后的词 */
    @TableField("term")
    private String term;

    /** 词频（该词在该片段中出现的次数） */
    @TableField("tf")
    private Integer tf;

    /** 片段长度（冗余存储，避免聚合） */
    @TableField("chunk_length")
    private Integer chunkLength;

    /** 片段原文（用于回显） */
    @TableField("content")
    private String content;

    /** 文档名（冗余存储，避免 JOIN） */
    @TableField("doc_name")
    private String docName;
}
