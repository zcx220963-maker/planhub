package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.RagDocument;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface RagDocumentMapper extends BaseMapper<RagDocument> {

    /**
     * 获取用户所有未删除的文档
     */
    @Select("SELECT * FROM rag_documents WHERE user_id = #{userId} AND status = 'active' ORDER BY created_at DESC")
    List<RagDocument> findActiveByUserId(@Param("userId") Long userId);

    /**
     * 软删除文档
     */
    @Update("UPDATE rag_documents SET status = 'deleted', deleted_at = NOW() WHERE id = #{id}")
    int softDeleteById(@Param("id") String id);
}
