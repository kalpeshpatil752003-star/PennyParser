package com.finassist.backend.controller;

import com.finassist.backend.dto.ChatMessageResponse;
import com.finassist.backend.entity.Chat;
import com.finassist.backend.entity.User;
import com.finassist.backend.service.ChatService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/chats")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping
    public ResponseEntity<Chat> createChat(@RequestBody(required = false) Map<String, String> body,
                                           @AuthenticationPrincipal User user) {
        String title = body != null ? body.get("title") : null;
        return ResponseEntity.ok(chatService.createChat(user, title));
    }

    @PostMapping("/{chatId}/messages")
    public ResponseEntity<ChatMessageResponse> ask(@PathVariable Long chatId,
                                                   @RequestBody Map<String, Object> body,
                                                   @AuthenticationPrincipal User user) {
        String question = (String) body.get("content");
        @SuppressWarnings("unchecked")
        List<Integer> rawIds = (List<Integer>) body.getOrDefault("documentIds", List.of());
        List<Long> documentIds = rawIds.stream().map(Integer::longValue).toList();

        return ResponseEntity.ok(chatService.askQuestion(chatId, user, question, documentIds));
    }

    @GetMapping("/{chatId}/messages")
    public ResponseEntity<List<com.finassist.backend.entity.ChatMessage>> getMessages(@PathVariable Long chatId,
                                                                                      @AuthenticationPrincipal User user) {
        return ResponseEntity.ok(chatService.getMessages(chatId, user.getId()));
    }

    @GetMapping
    public ResponseEntity<List<Chat>> listChats(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(chatService.getChatsForUser(user.getId()));
    }

    @PutMapping("/{chatId}")
    public ResponseEntity<Chat> renameChat(@PathVariable Long chatId,
                                           @RequestBody Map<String, String> body,
                                           @AuthenticationPrincipal User user) {
        String title = body.get("title");
        return ResponseEntity.ok(chatService.renameChat(chatId, user.getId(), title));
    }

    @DeleteMapping("/{chatId}")
    public ResponseEntity<Void> deleteChat(@PathVariable Long chatId,
                                           @AuthenticationPrincipal User user) {
        chatService.deleteChat(chatId, user.getId());
        return ResponseEntity.noContent().build();
    }
}