package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.RagBm25Index;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface RagBm25IndexMapper extends BaseMapper<RagBm25Index> {

    /**
     * 删除指定文档的所有索引
     */
    @Delete("DELETE FROM rag_bm25_index WHERE doc_id = #{docId}")
    int deleteByDocId(@Param("docId") String docId);
}
