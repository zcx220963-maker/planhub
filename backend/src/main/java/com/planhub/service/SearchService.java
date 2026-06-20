package com.planhub.service;

import com.planhub.dto.response.SearchResponse;

import java.util.List;

public interface SearchService {
    SearchResponse search(String query, String type, int page, int size);
    List<String> getSuggestions(String query);
    void syncAllPostHashtagsToTopics();
}
