package com.planhub.controller;

import com.planhub.dto.response.ApiResponse;
import com.planhub.dto.response.SearchResponse;
import com.planhub.service.SearchService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/search")
public class SearchController {
    private final SearchService searchService;

    public SearchController(SearchService searchService) {
        this.searchService = searchService;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<SearchResponse>> search(
            @RequestParam String q,
            @RequestParam(defaultValue = "all") String type,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        SearchResponse response = searchService.search(q, type, page, size);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/suggestions")
    public ResponseEntity<ApiResponse<List<String>>> getSuggestions(@RequestParam String q) {
        List<String> suggestions = searchService.getSuggestions(q);
        return ResponseEntity.ok(ApiResponse.success(suggestions));
    }

    @PostMapping("/sync-topics")
    public ResponseEntity<ApiResponse<String>> syncTopics() {
        searchService.syncAllPostHashtagsToTopics();
        return ResponseEntity.ok(ApiResponse.success("话题同步完成"));
    }
}
