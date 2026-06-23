package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.planhub.entity.Notification;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface NotificationMapper extends BaseMapper<Notification> {
    
    @Select("SELECT * FROM notifications WHERE user_id = #{userId} ORDER BY created_at DESC")
    IPage<Notification> selectByUserIdOrderByCreatedAtDesc(@Param("userId") Long userId, Page<Notification> page);
    
    @Select("SELECT * FROM notifications WHERE user_id = #{userId} AND is_read = #{isRead} ORDER BY created_at DESC")
    IPage<Notification> selectByUserIdAndIsReadOrderByCreatedAtDesc(
            @Param("userId") Long userId, 
            @Param("isRead") Boolean isRead, 
            Page<Notification> page);
    
    @Select("SELECT COUNT(*) FROM notifications WHERE user_id = #{userId} AND is_read = #{isRead}")
    long countByUserIdAndIsRead(@Param("userId") Long userId, @Param("isRead") Boolean isRead);
    
    @Update("UPDATE notifications SET is_read = true WHERE id = #{notificationId}")
    void markAsRead(@Param("notificationId") Long notificationId);
    
    @Update("UPDATE notifications SET is_read = true WHERE user_id = #{userId}")
    void markAllAsRead(@Param("userId") Long userId);
    
    @Select("SELECT * FROM notifications WHERE user_id = #{userId} ORDER BY created_at DESC")
    List<Notification> selectByUserIdOrderByCreatedAtDesc(@Param("userId") Long userId);
    
    @Update("<script>UPDATE notifications SET is_read = true WHERE id IN <foreach item='id' collection='ids' open='(' separator=',' close=')'>#{id}</foreach> AND user_id = #{userId}</script>")
    void markMultipleAsRead(@Param("ids") List<Long> ids, @Param("userId") Long userId);
    
    @Delete("<script>DELETE FROM notifications WHERE id IN <foreach item='id' collection='ids' open='(' separator=',' close=')'>#{id}</foreach> AND user_id = #{userId}</script>")
    void deleteMultipleNotifications(@Param("ids") List<Long> ids, @Param("userId") Long userId);
}
