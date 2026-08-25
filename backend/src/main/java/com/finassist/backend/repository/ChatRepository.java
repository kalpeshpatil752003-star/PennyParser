package com.finassist.backend.repository;

import com.finassist.backend.entity.Chat;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

import java.util.Optional;

public interface ChatRepository extends JpaRepository<Chat, Long> {
    List<Chat> findByUserId(Long userId);
    Optional<Chat> findByIdAndUserId(Long id, Long userId);
}