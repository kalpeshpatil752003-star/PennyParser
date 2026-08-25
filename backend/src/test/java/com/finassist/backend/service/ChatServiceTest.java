package com.finassist.backend.service;

import com.finassist.backend.client.PythonAiServiceClient;
import com.finassist.backend.dto.ChatMessageResponse;
import com.finassist.backend.entity.Chat;
import com.finassist.backend.entity.Document;
import com.finassist.backend.entity.User;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.repository.ChatMessageRepository;
import com.finassist.backend.repository.ChatRepository;
import com.finassist.backend.repository.DocumentRepository;
import com.finassist.backend.repository.MessageCitationRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class ChatServiceTest {

    private ChatRepository chatRepository;
    private ChatMessageRepository messageRepository;
    private MessageCitationRepository citationRepository;
    private DocumentRepository documentRepository;
    private PythonAiServiceClient aiServiceClient;
    private ChatService chatService;

    private User userA;
    private User userB;

    @BeforeEach
    void setUp() {
        chatRepository = mock(ChatRepository.class);
        messageRepository = mock(ChatMessageRepository.class);
        citationRepository = mock(MessageCitationRepository.class);
        documentRepository = mock(DocumentRepository.class);
        aiServiceClient = mock(PythonAiServiceClient.class);
        chatService = new ChatService(chatRepository, messageRepository, citationRepository, documentRepository, aiServiceClient);

        userA = new User();
        userA.setId(1L);
        userA.setEmail("usera@example.com");

        userB = new User();
        userB.setId(2L);
        userB.setEmail("userb@example.com");
    }

    @Test
    void askQuestion_belongingToUser_success() {
        Chat chat = new Chat();
        chat.setId(10L);
        chat.setUser(userA);

        when(chatRepository.findByIdAndUserId(10L, 1L)).thenReturn(Optional.of(chat));
        when(documentRepository.findAllByIdInAndUploadedById(List.of(100L), 1L))
                .thenReturn(List.of(new Document()));
        when(aiServiceClient.query(any(), any()))
                .thenReturn(new PythonAiServiceClient.QueryResult("AI Answer", List.of()));

        ChatMessageResponse response = chatService.askQuestion(10L, userA, "What is revenue?", List.of(100L));

        assertNotNull(response);
        assertEquals("AI Answer", response.getContent());
    }

    @Test
    void askQuestion_otherUserChat_throwsNotFound() {
        when(chatRepository.findByIdAndUserId(10L, 1L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () ->
                chatService.askQuestion(10L, userA, "Question", List.of()));
        assertEquals("Chat not found", ex.getMessage());
    }

    @Test
    void askQuestion_unauthorizedDocument_throwsNotFound() {
        Chat chat = new Chat();
        chat.setId(10L);
        chat.setUser(userA);

        when(chatRepository.findByIdAndUserId(10L, 1L)).thenReturn(Optional.of(chat));
        when(documentRepository.findAllByIdInAndUploadedById(List.of(999L), 1L))
                .thenReturn(List.of());

        ApiException ex = assertThrows(ApiException.class, () ->
                chatService.askQuestion(10L, userA, "Question", List.of(999L)));
        assertEquals("Document not found or access denied", ex.getMessage());
        verify(aiServiceClient, never()).query(any(), any());
    }

    @Test
    void getMessages_otherUserChat_throwsNotFound() {
        when(chatRepository.findByIdAndUserId(10L, 2L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () ->
                chatService.getMessages(10L, userB.getId()));
        assertEquals("Chat not found", ex.getMessage());
    }
}
