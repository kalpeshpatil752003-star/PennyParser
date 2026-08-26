package com.finassist.backend.service;

import com.finassist.backend.client.PythonAiServiceClient;
import com.finassist.backend.dto.ChatMessageResponse;
import com.finassist.backend.entity.*;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
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
    private Document doc10;
    private Document doc11;

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

        doc10 = new Document();
        doc10.setId(10L);
        doc10.setUploadedBy(userA);

        doc11 = new Document();
        doc11.setId(11L);
        doc11.setUploadedBy(userA);
    }

    // =====================================================
    // Test 1: Associate document and verify persistence
    // =====================================================
    @Test
    void askQuestion_firstQuestionWithDocIds_persistsAssociation() {
        Chat chat = new Chat();
        chat.setId(1L);
        chat.setUser(userA);
        chat.setDocuments(new HashSet<>());

        when(chatRepository.findByIdAndUserId(1L, 1L)).thenReturn(Optional.of(chat));
        when(documentRepository.findAllByIdInAndUploadedById(List.of(10L), 1L))
                .thenReturn(List.of(doc10));
        when(chatRepository.save(any(Chat.class))).thenAnswer(inv -> inv.getArgument(0));
        when(aiServiceClient.query(any(), any()))
                .thenReturn(new PythonAiServiceClient.QueryResult("Revenue is $60B", List.of()));

        chatService.askQuestion(1L, userA, "What is revenue?", List.of(10L));

        // Verify: chat now has document 10 associated
        assertTrue(chat.getDocuments().contains(doc10));
        // Verify: Python received [10]
        verify(aiServiceClient).query(eq("What is revenue?"), eq(List.of(10L)));
    }

    // =====================================================
    // Test 2: KEY REGRESSION — empty documentIds still resolves from persisted state
    // =====================================================
    @Test
    void askQuestion_subsequentQuestionWithEmptyDocIds_usesPersistedAssociation() {
        Chat chat = new Chat();
        chat.setId(1L);
        chat.setUser(userA);
        // Simulate: doc10 was already associated from the first question
        chat.setDocuments(new HashSet<>(Set.of(doc10)));

        when(chatRepository.findByIdAndUserId(1L, 1L)).thenReturn(Optional.of(chat));
        when(chatRepository.save(any(Chat.class))).thenAnswer(inv -> inv.getArgument(0));
        when(aiServiceClient.query(any(), any()))
                .thenReturn(new PythonAiServiceClient.QueryResult("Net income is $18B", List.of()));

        // Send question with EMPTY documentIds — simulating reopened chat
        chatService.askQuestion(1L, userA, "What about net income?", List.of());

        // CRITICAL ASSERTION: Python must still receive [10] from persisted state
        verify(aiServiceClient).query(eq("What about net income?"), eq(List.of(10L)));
    }

    // =====================================================
    // Test 3: Chat retains documents after reload
    // =====================================================
    @Test
    void askQuestion_nullDocumentIds_usesPersistedAssociation() {
        Chat chat = new Chat();
        chat.setId(1L);
        chat.setUser(userA);
        chat.setDocuments(new HashSet<>(Set.of(doc10)));

        when(chatRepository.findByIdAndUserId(1L, 1L)).thenReturn(Optional.of(chat));
        when(chatRepository.save(any(Chat.class))).thenAnswer(inv -> inv.getArgument(0));
        when(aiServiceClient.query(any(), any()))
                .thenReturn(new PythonAiServiceClient.QueryResult("Answer", List.of()));

        // null documentIds — client didn't send the field at all
        chatService.askQuestion(1L, userA, "What about Q2?", null);

        verify(aiServiceClient).query(eq("What about Q2?"), eq(List.of(10L)));
    }

    // =====================================================
    // Test 5: User A cannot use User B's document
    // =====================================================
    @Test
    void askQuestion_unauthorizedDocument_throwsNotFound() {
        Chat chat = new Chat();
        chat.setId(1L);
        chat.setUser(userA);
        chat.setDocuments(new HashSet<>());

        when(chatRepository.findByIdAndUserId(1L, 1L)).thenReturn(Optional.of(chat));
        // User A asks for doc 999 which doesn't belong to them
        when(documentRepository.findAllByIdInAndUploadedById(List.of(999L), 1L))
                .thenReturn(List.of());  // empty: doc not found for this user

        ApiException ex = assertThrows(ApiException.class, () ->
                chatService.askQuestion(1L, userA, "Question", List.of(999L)));
        assertEquals("Document not found or access denied", ex.getMessage());
        verify(aiServiceClient, never()).query(any(), any());
    }

    // =====================================================
    // Test 5b: User A cannot access User B's chat
    // =====================================================
    @Test
    void askQuestion_otherUserChat_throwsNotFound() {
        when(chatRepository.findByIdAndUserId(10L, 1L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () ->
                chatService.askQuestion(10L, userA, "Question", List.of()));
        assertEquals("Chat not found", ex.getMessage());
    }

    // =====================================================
    // Test 6: Deleting document doesn't delete chat
    // (tested via entity relationship — chat_documents cascade on document delete)
    // =====================================================

    // =====================================================
    // Test 7: Deleting chat doesn't delete document
    // =====================================================
    @Test
    void deleteChat_doesNotDeleteDocuments() {
        Chat chat = new Chat();
        chat.setId(1L);
        chat.setUser(userA);
        chat.setDocuments(new HashSet<>(Set.of(doc10)));

        when(chatRepository.findByIdAndUserId(1L, 1L)).thenReturn(Optional.of(chat));

        chatService.deleteChat(1L, 1L);

        // Verify: chat was deleted
        verify(chatRepository).delete(chat);
        // Verify: document repository delete was NEVER called
        verify(documentRepository, never()).delete(any());
    }

    // =====================================================
    // Test 8: Multi-document chat
    // =====================================================
    @Test
    void askQuestion_multiDocumentChat_sendsAllPersistedDocIds() {
        Chat chat = new Chat();
        chat.setId(1L);
        chat.setUser(userA);
        chat.setDocuments(new HashSet<>(Set.of(doc10, doc11)));

        when(chatRepository.findByIdAndUserId(1L, 1L)).thenReturn(Optional.of(chat));
        when(chatRepository.save(any(Chat.class))).thenAnswer(inv -> inv.getArgument(0));
        when(aiServiceClient.query(any(), any()))
                .thenReturn(new PythonAiServiceClient.QueryResult("Comparison", List.of()));

        // No documentIds in request — uses persisted association
        chatService.askQuestion(1L, userA, "Compare revenues", List.of());

        // Python must receive BOTH [10, 11] (sorted)
        verify(aiServiceClient).query(eq("Compare revenues"), eq(List.of(10L, 11L)));
    }

    // =====================================================
    // Test: getMessages with wrong user throws
    // =====================================================
    @Test
    void getMessages_otherUserChat_throwsNotFound() {
        when(chatRepository.findByIdAndUserId(10L, 2L)).thenReturn(Optional.empty());

        ApiException ex = assertThrows(ApiException.class, () ->
                chatService.getMessages(10L, userB.getId()));
        assertEquals("Chat not found", ex.getMessage());
    }

    // =====================================================
    // Test: additive association — new docs merge with existing
    // =====================================================
    @Test
    void askQuestion_additionalDocument_mergesWithExisting() {
        Chat chat = new Chat();
        chat.setId(1L);
        chat.setUser(userA);
        chat.setDocuments(new HashSet<>(Set.of(doc10)));

        when(chatRepository.findByIdAndUserId(1L, 1L)).thenReturn(Optional.of(chat));
        when(documentRepository.findAllByIdInAndUploadedById(List.of(11L), 1L))
                .thenReturn(List.of(doc11));
        when(chatRepository.save(any(Chat.class))).thenAnswer(inv -> inv.getArgument(0));
        when(aiServiceClient.query(any(), any()))
                .thenReturn(new PythonAiServiceClient.QueryResult("Merged", List.of()));

        // Add doc11 to a chat that already has doc10
        chatService.askQuestion(1L, userA, "Compare", List.of(11L));

        // Chat now has both documents
        assertEquals(2, chat.getDocuments().size());
        assertTrue(chat.getDocuments().contains(doc10));
        assertTrue(chat.getDocuments().contains(doc11));
        // Python receives both
        verify(aiServiceClient).query(eq("Compare"), eq(List.of(10L, 11L)));
    }
}
