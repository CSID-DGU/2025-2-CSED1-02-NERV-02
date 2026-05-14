package com.nerv.overlay.repository;

import com.nerv.overlay.entity.ChzzkToken;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ChzzkTokenRepository extends JpaRepository<ChzzkToken, Long> {

    Optional<ChzzkToken> findByUserId(Long userId);

    void deleteByUserId(Long userId);
}
