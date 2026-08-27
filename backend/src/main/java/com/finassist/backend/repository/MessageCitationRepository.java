package com.finassist.backend.repository;

import com.finassist.backend.entity.MessageCitation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface MessageCitationRepository extends JpaRepository<MessageCitation, Long> {
    List<MessageCitation> findByMessageIdIn(List<Long> messageIds);
    List<MessageCitation> findByMessage_Chat_Id(Long chatId);
}