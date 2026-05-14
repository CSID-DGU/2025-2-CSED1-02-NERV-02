package com.nerv.overlay.repository;

import com.nerv.overlay.entity.OverlayConfig;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface OverlayConfigRepository extends JpaRepository<OverlayConfig, Long> {

    Optional<OverlayConfig> findByOverlayToken(String overlayToken);

    boolean existsByOverlayToken(String overlayToken);

    /** 본인 오버레이. */
    Optional<OverlayConfig> findFirstByOwnerUserId(Long ownerUserId);

    /** 비로그인용 글로벌 더미 (owner NULL). */
    Optional<OverlayConfig> findFirstByOwnerUserIdIsNull();
}
