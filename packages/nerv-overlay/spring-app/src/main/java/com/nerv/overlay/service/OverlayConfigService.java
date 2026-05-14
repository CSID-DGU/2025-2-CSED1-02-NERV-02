package com.nerv.overlay.service;

import com.nerv.overlay.dto.OverlayConfigDto;
import com.nerv.overlay.dto.OverlayConfigRequest;
import com.nerv.overlay.entity.OverlayConfig;
import com.nerv.overlay.entity.OverlayDictionary;
import com.nerv.overlay.repository.OverlayConfigRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

@Slf4j
@Service
@RequiredArgsConstructor
public class OverlayConfigService {

    private final OverlayConfigRepository repository;

    @Value("${app.public-base-url:http://localhost:8080}")
    private String publicBaseUrl;

    private static final SecureRandom RANDOM = new SecureRandom();

    /** 오버레이 새로 생성. overlay_token 자동 발급. ownerUserId NULL = 글로벌 더미. */
    @Transactional
    public OverlayConfigDto create(Long ownerUserId, OverlayConfigRequest req) {
        OverlayConfig entity = OverlayConfig.builder()
                .ownerUserId(ownerUserId)
                .overlayToken(generateUniqueToken())
                .name(req.name() != null ? req.name() : "내 오버레이")
                .channelId(req.channelId())
                .source(req.source() != null ? req.source() : "DUMMY")
                .securityLevel(req.securityLevel() != null ? req.securityLevel() : "MEDIUM")
                .blockDisplayMode(req.blockDisplayMode() != null ? req.blockDisplayMode() : "MASK")
                .placeholderText(req.placeholderText() != null ? req.placeholderText() : "[필터됨]")
                .showScore(req.showScore() != null ? req.showScore() : false)
                .build();

        applyDictionary(entity, req.whitelist(), req.blacklist());

        OverlayConfig saved = repository.save(entity);
        log.info("[OverlayConfig] 생성: id={} owner={} token={}",
                saved.getId(), ownerUserId, saved.getOverlayToken());
        return OverlayConfigDto.from(saved, publicBaseUrl);
    }

    /** 토큰으로 조회 — 오버레이 페이지 로드 시 */
    @Transactional(readOnly = true)
    public OverlayConfigDto findByToken(String overlayToken) {
        OverlayConfig entity = repository.findByOverlayToken(overlayToken)
                .orElseThrow(() -> new IllegalArgumentException("오버레이를 찾을 수 없습니다: " + overlayToken));
        return OverlayConfigDto.from(entity, publicBaseUrl);
    }

    /** ID로 조회 (관리용) */
    @Transactional(readOnly = true)
    public OverlayConfigDto findById(Long id) {
        OverlayConfig entity = repository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("오버레이를 찾을 수 없습니다: id=" + id));
        return OverlayConfigDto.from(entity, publicBaseUrl);
    }

    @Transactional(readOnly = true)
    public List<OverlayConfigDto> findAll() {
        return repository.findAll().stream()
                .map(e -> OverlayConfigDto.from(e, publicBaseUrl))
                .toList();
    }

    /**
     * 본인(또는 비로그인용 글로벌 더미) 활성 오버레이.
     * 없으면 더미 기본값으로 자동 생성.
     */
    @Transactional
    public OverlayConfigDto getOrCreateActive(Long userId) {
        Optional<OverlayConfig> existing = (userId == null)
                ? repository.findFirstByOwnerUserIdIsNull()
                : repository.findFirstByOwnerUserId(userId);

        return existing
                .map(e -> OverlayConfigDto.from(e, publicBaseUrl))
                .orElseGet(() -> create(userId, new OverlayConfigRequest(
                        "더미테스트",
                        null,           // channel_id
                        "DUMMY",        // source
                        "MEDIUM",       // security_level
                        "MASK",         // block_display_mode
                        "[필터됨]",      // placeholder_text
                        false,          // show_score
                        List.of(),      // whitelist
                        List.of()       // blacklist
                )));
    }

    /** 본인 활성 오버레이 갱신 — 없으면 생성 후 갱신 */
    @Transactional
    public OverlayConfigDto updateActive(Long userId, OverlayConfigRequest req) {
        Optional<OverlayConfig> existing = (userId == null)
                ? repository.findFirstByOwnerUserIdIsNull()
                : repository.findFirstByOwnerUserId(userId);

        OverlayConfig entity = existing.orElseGet(() -> {
            OverlayConfigDto created = getOrCreateActive(userId);
            return repository.findById(created.id()).orElseThrow();
        });
        return update(entity.getId(), req);
    }

    /** ownerUserId 만 다른 컨트롤러에서 직접 갱신할 때 사용 (예: 치지직 연동 시 채널/소스 자동 세팅). */
    @Transactional
    public OverlayConfigDto applyChzzkConnection(Long userId, String channelId) {
        OverlayConfig entity = repository.findFirstByOwnerUserId(userId)
                .orElseGet(() -> {
                    OverlayConfigDto created = getOrCreateActive(userId);
                    return repository.findById(created.id()).orElseThrow();
                });
        entity.setSource("CHZZK");
        entity.setChannelId(channelId);
        log.info("[OverlayConfig] 치지직 연동 적용: userId={} channelId={}", userId, channelId);
        return OverlayConfigDto.from(entity, publicBaseUrl);
    }

    /** 치지직 해제 — 더미로 되돌림. */
    @Transactional
    public OverlayConfigDto removeChzzkConnection(Long userId) {
        OverlayConfig entity = repository.findFirstByOwnerUserId(userId)
                .orElseThrow(() -> new IllegalArgumentException("오버레이가 없습니다."));
        entity.setSource("DUMMY");
        entity.setChannelId(null);
        log.info("[OverlayConfig] 치지직 연동 해제: userId={}", userId);
        return OverlayConfigDto.from(entity, publicBaseUrl);
    }

    /** 부분 갱신 — null 필드는 변경 안 함 */
    @Transactional
    public OverlayConfigDto update(Long id, OverlayConfigRequest req) {
        OverlayConfig entity = repository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("오버레이를 찾을 수 없습니다: id=" + id));

        if (req.name() != null) entity.setName(req.name());
        if (req.channelId() != null) entity.setChannelId(req.channelId());
        if (req.source() != null) entity.setSource(req.source());
        if (req.securityLevel() != null) entity.setSecurityLevel(req.securityLevel());
        if (req.blockDisplayMode() != null) entity.setBlockDisplayMode(req.blockDisplayMode());
        if (req.placeholderText() != null) entity.setPlaceholderText(req.placeholderText());
        if (req.showScore() != null) entity.setShowScore(req.showScore());

        // 사전은 들어왔으면 통째로 교체 (단순 모델)
        if (req.whitelist() != null || req.blacklist() != null) {
            entity.getDictionary().clear();
            applyDictionary(entity,
                    req.whitelist() != null ? req.whitelist() : List.of(),
                    req.blacklist() != null ? req.blacklist() : List.of());
        }

        log.info("[OverlayConfig] 수정: id={}", entity.getId());
        return OverlayConfigDto.from(entity, publicBaseUrl);
    }

    @Transactional
    public void delete(Long id) {
        if (!repository.existsById(id)) {
            throw new IllegalArgumentException("오버레이를 찾을 수 없습니다: id=" + id);
        }
        repository.deleteById(id);
        log.info("[OverlayConfig] 삭제: id={}", id);
    }

    // ─── 내부 헬퍼 ───

    private String generateUniqueToken() {
        // 충돌 확률 매우 낮지만 안전 장치로 5회 시도
        for (int i = 0; i < 5; i++) {
            String token = newRandomToken();
            if (!repository.existsByOverlayToken(token)) {
                return token;
            }
        }
        throw new IllegalStateException("토큰 생성 실패 — 5회 충돌");
    }

    private String newRandomToken() {
        byte[] bytes = new byte[12];  // base64 → 16자
        RANDOM.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private void applyDictionary(OverlayConfig entity, List<String> whitelist, List<String> blacklist) {
        Set<String> seen = new HashSet<>();
        if (whitelist != null) {
            for (String w : whitelist) {
                if (w == null || w.isBlank()) continue;
                String word = w.trim();
                if (seen.add("W:" + word)) {
                    entity.getDictionary().add(OverlayDictionary.builder()
                            .overlayConfig(entity)
                            .word(word)
                            .listType("WHITELIST")
                            .build());
                }
            }
        }
        if (blacklist != null) {
            for (String b : blacklist) {
                if (b == null || b.isBlank()) continue;
                String word = b.trim();
                if (seen.add("B:" + word)) {
                    entity.getDictionary().add(OverlayDictionary.builder()
                            .overlayConfig(entity)
                            .word(word)
                            .listType("BLACKLIST")
                            .build());
                }
            }
        }
    }
}
