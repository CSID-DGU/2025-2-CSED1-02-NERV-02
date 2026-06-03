package com.nerv.overlay.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 한 방송 세션 동안 필터링된(action ≠ NORMAL) 메시지 1건.
 * selected_for_relearn 은 사용자가 한 번 체크하면 영구히 true (중복 재학습 방지).
 */
@Entity
@Table(name = "filtered_messages")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FilteredMessage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "session_id", nullable = false)
    private Long sessionId;

    @Column(nullable = false, length = 100)
    private String author;

    @Column(name = "original_text", nullable = false, columnDefinition = "TEXT")
    private String originalText;

    @Column(name = "masked_text", columnDefinition = "TEXT")
    private String maskedText;

    @Column(nullable = false, length = 20)
    private String action;

    @Column(nullable = false, precision = 4, scale = 3)
    @Builder.Default
    private BigDecimal score = BigDecimal.ZERO;

    /** "word|type,word|type" 형태로 직렬화. JSON 인데 단순화. */
    @Column(name = "detected_words", columnDefinition = "TEXT")
    private String detectedWords;

    @Column(name = "selected_for_relearn", nullable = false)
    @Builder.Default
    private Boolean selectedForRelearn = false;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
