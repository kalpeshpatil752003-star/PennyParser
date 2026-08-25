package com.finassist.backend.service;

import com.finassist.backend.client.PythonAiServiceClient;
import com.finassist.backend.dto.ChatMessageResponse;
import com.finassist.backend.entity.*;
import com.finassist.backend.exception.ApiException;
import com.finassist.backend.repository.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ChatService {

    private final ChatRepository chatRepository;
    private final ChatMessageRepository messageRepository;
    private final MessageCitationRepository citationRepository;
    private final DocumentRepository documentRepository;
    private final PythonAiServiceClient aiServiceClient;

    public ChatService(ChatRepository chatRepository, ChatMessageRepository messageRepository,
                       MessageCitationRepository citationRepository, DocumentRepository documentRepository,
                       PythonAiServiceClient aiServiceClient) {
        this.chatRepository = chatRepository;
        this.messageRepository = messageRepository;
        this.citationRepository = citationRepository;
        this.documentRepository = documentRepository;
        this.aiServiceClient = aiServiceClient;
    }

    public Chat createChat(User user, String title) {
        Chat chat = new Chat();
        chat.setUser(user);
        chat.setTitle(title != null ? title : "New Conversation");
        return chatRepository.save(chat);
    }

    public ChatMessageResponse askQuestion(Long chatId, User user, String question, List<Long> documentIds) {
        Chat chat = chatRepository.findByIdAndUserId(chatId, user.getId())
                .orElseThrow(() -> new ApiException("Chat not found", HttpStatus.NOT_FOUND));

        if (documentIds != null && !documentIds.isEmpty()) {
            List<Document> userDocs = documentRepository.findAllByIdInAndUploadedById(documentIds, user.getId());
            if (userDocs.size() != documentIds.stream().distinct().count()) {
                throw new ApiException("Document not found or access denied", HttpStatus.NOT_FOUND);
            }
        }

        ChatMessage userMessage = new ChatMessage();
        userMessage.setChat(chat);
        userMessage.setRole(MessageRole.USER);
        userMessage.setContent(question);
        messageRepository.save(userMessage);

        var result = aiServiceClient.query(question, documentIds != null ? documentIds : List.of());

        ChatMessage assistantMessage = new ChatMessage();
        assistantMessage.setChat(chat);
        assistantMessage.setRole(MessageRole.ASSISTANT);
        assistantMessage.setContent(result.answer());
        messageRepository.save(assistantMessage);

        List<ChatMessageResponse.CitationDto> citationDtos = result.citations().stream()
                .map(c -> {
                    MessageCitation citation = new MessageCitation();
                    citation.setMessage(assistantMessage);
                    citation.setDocumentId(c.documentId());
                    citation.setPageNumber(c.page());
                    citationRepository.save(citation);
                    return new ChatMessageResponse.CitationDto(c.documentId(), c.page());
                }).toList();

        return new ChatMessageResponse(assistantMessage.getId(), MessageRole.ASSISTANT,
                assistantMessage.getContent(), citationDtos, assistantMessage.getCreatedAt());
    }

    public List<ChatMessage> getMessages(Long chatId, Long userId) {
        chatRepository.findByIdAndUserId(chatId, userId)
                .orElseThrow(() -> new ApiException("Chat not found", HttpStatus.NOT_FOUND));
        return messageRepository.findByChatIdOrderByCreatedAtAsc(chatId);
    }

    public List<Chat> getChatsForUser(Long userId) {
        return chatRepository.findByUserId(userId);
    }

    public Chat renameChat(Long chatId, Long userId, String title) {
        Chat chat = chatRepository.findByIdAndUserId(chatId, userId)
                .orElseThrow(() -> new ApiException("Chat not found", HttpStatus.NOT_FOUND));
        chat.setTitle(title);
        return chatRepository.save(chat);
    }

    public void deleteChat(Long chatId, Long userId) {
        Chat chat = chatRepository.findByIdAndUserId(chatId, userId)
                .orElseThrow(() -> new ApiException("Chat not found", HttpStatus.NOT_FOUND));
        chatRepository.delete(chat);
    }
}