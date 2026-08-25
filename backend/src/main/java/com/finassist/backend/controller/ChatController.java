package com.finassist.backend.controller;

import com.finassist.backend.dto.ChatMessageResponse;
import com.finassist.backend.entity.Chat;
import com.finassist.backend.entity.User;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.service.ChatService;
import org.springframework.http.HttpStatus;
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

    @PostMapping("/ask")
    public ResponseEntity<ChatMessageResponse> askQuick(@RequestBody Map<String, Object> body,
                                                        @AuthenticationPrincipal User user) {
        String question = (String) body.get("message");
        if (question == null) {
            question = (String) body.get("content");
        }
        if (question == null || question.trim().isEmpty()) {
            throw new ApiException("Question content cannot be empty", HttpStatus.BAD_REQUEST);
        }

        @SuppressWarnings("unchecked")
        List<Number> rawIds = (List<Number>) body.getOrDefault("documentIds", List.of());
        List<Long> documentIds = rawIds != null ? rawIds.stream().map(Number::longValue).toList() : List.of();

        Long chatId = body.containsKey("chatId") && body.get("chatId") != null ? ((Number) body.get("chatId")).longValue() : null;
        if (chatId == null) {
            Chat chat = chatService.createChat(user, "New Research Chat");
            chatId = chat.getId();
        }

        return ResponseEntity.ok(chatService.askQuestion(chatId, user, question, documentIds));
    }

    @PostMapping("/{chatId}/messages")
    public ResponseEntity<ChatMessageResponse> askInChat(@PathVariable Long chatId,
                                                         @RequestBody Map<String, Object> body,
                                                         @AuthenticationPrincipal User user) {
        String question = (String) body.get("content");
        if (question == null) {
            question = (String) body.get("message");
        }
        if (question == null || question.trim().isEmpty()) {
            throw new ApiException("Question content cannot be empty", HttpStatus.BAD_REQUEST);
        }

        @SuppressWarnings("unchecked")
        List<Number> rawIds = (List<Number>) body.getOrDefault("documentIds", List.of());
        List<Long> documentIds = rawIds != null ? rawIds.stream().map(Number::longValue).toList() : List.of();

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