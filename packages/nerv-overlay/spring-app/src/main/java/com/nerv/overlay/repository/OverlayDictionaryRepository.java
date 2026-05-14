package com.nerv.overlay.repository;

import com.nerv.overlay.entity.OverlayDictionary;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OverlayDictionaryRepository extends JpaRepository<OverlayDictionary, Long> {

    List<OverlayDictionary> findByOverlayConfigId(Long overlayId);

    List<OverlayDictionary> findByOverlayConfigIdAndListType(Long overlayId, String listType);

    void deleteByOverlayConfigIdAndWordAndListType(Long overlayId, String word, String listType);
}
