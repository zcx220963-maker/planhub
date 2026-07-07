package com.planhub.service;

import com.planhub.dto.response.SearchResponse;

import java.util.List;

public interface SearchService {
    SearchResponse search(String query, String type, int page, int size);
    SearchResponse search(String query, String type, int page, int size, Long currentUserId);
    List<String> getSuggestions(String query);
    void syncAllPostHashtagsToTopics();
}
