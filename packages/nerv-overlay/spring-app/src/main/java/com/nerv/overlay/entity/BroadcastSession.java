package com.nerv.overlay.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

/**
 * 한 사용자의 한 방송 세션. 채팅이 처음 도착하면 새 세션이 생성되고,
 * 일정 시간 동안 메시지가 없으면 자동으로 종료(ended_at 채워짐) 처리된다.
 */
@Entity
@Table(name = "broadcast_sessions")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class BroadcastSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "owner_user_id", nullable = false)
    private Long ownerUserId;

    @Column(nullable = false, length = 20)
    private String source;

    @Column(name = "channel_id", length = 100)
    private String channelId;

    @Column(name = "started_at", nullable = false)
    private LocalDateTime startedAt;

    @Column(name = "last_message_at", nullable = false)
    private LocalDateTime lastMessageAt;

    /** NULL = 진행 중, 값 있으면 종료된 방송. */
    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    @Column(name = "message_count", nullable = false)
    @Builder.Default
    private Integer messageCount = 0;

    @Column(name = "filtered_count", nullable = false)
    @Builder.Default
    private Integer filteredCount = 0;
}
