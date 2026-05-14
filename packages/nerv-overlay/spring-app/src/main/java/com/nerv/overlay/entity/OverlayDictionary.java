package com.nerv.overlay.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * 오버레이별 화이트/블랙리스트 단어.
 */
@Entity
@Table(name = "overlay_dictionary",
       uniqueConstraints = @UniqueConstraint(name = "uq_overlay_word",
                                              columnNames = {"overlay_id", "word", "list_type"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class OverlayDictionary {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "overlay_id", nullable = false)
    private OverlayConfig overlayConfig;

    @Column(nullable = false, length = 100)
    private String word;

    @Column(name = "list_type", nullable = false, length = 20)
    private String listType;  // WHITELIST / BLACKLIST

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
