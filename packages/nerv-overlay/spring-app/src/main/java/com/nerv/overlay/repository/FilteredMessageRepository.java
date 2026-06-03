package com.nerv.overlay.repository;

import com.nerv.overlay.entity.FilteredMessage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface FilteredMessageRepository extends JpaRepository<FilteredMessage, Long> {

    /** 세션의 필터링된 메시지 (오래된 순). */
    List<FilteredMessage> findBySessionIdOrderByCreatedAtAsc(Long sessionId);
}
