package com.nerv.overlay.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 오버레이 설정 — OBS Browser Source URL 1개당 row 1개.
 * overlay_token 이 공개 URL 슬러그.
 */
@Entity
@Table(name = "overlay_configs")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class OverlayConfig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 소유자. NULL = 비로그인용 글로벌 더미. */
    @Column(name = "owner_user_id")
    private Long ownerUserId;

    @Column(name = "overlay_token", nullable = false, unique = true, length = 32)
    private String overlayToken;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "channel_id", length = 100)
    private String channelId;

    @Column(nullable = false, length = 20)
    @Builder.Default
    private String source = "DUMMY";  // DUMMY / CHZZK / YOUTUBE

    @Column(name = "security_level", nullable = false, length = 10)
    @Builder.Default
    private String securityLevel = "MEDIUM";

    @Column(name = "block_display_mode", nullable = false, length = 20)
    @Builder.Default
    private String blockDisplayMode = "MASK";  // MASK / HIDE / PLACEHOLDER

    @Column(name = "placeholder_text", nullable = false, length = 50)
    @Builder.Default
    private String placeholderText = "[필터됨]";

    @Column(name = "show_score", nullable = false)
    @Builder.Default
    private Boolean showScore = false;

    @Column(name = "style_config_json", columnDefinition = "TEXT")
    private String styleConfigJson;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @OneToMany(mappedBy = "overlayConfig", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<OverlayDictionary> dictionary = new ArrayList<>();
}
