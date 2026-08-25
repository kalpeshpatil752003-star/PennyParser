package com.finassist.backend.repository;

import com.finassist.backend.entity.MessageCitation;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MessageCitationRepository extends JpaRepository<MessageCitation, Long> {}