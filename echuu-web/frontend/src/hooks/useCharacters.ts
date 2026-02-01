import { useState, useEffect, useCallback } from "react";
import type { CharacterProfile, CharacterCreate } from "../types";
import {
  fetchCharacters,
  createCharacter as apiCreateCharacter,
  updateCharacter as apiUpdateCharacter,
  deleteCharacter as apiDeleteCharacter,
} from "../api/charactersApi";

export const useCharacters = () => {
  const [characters, setCharacters] = useState<CharacterProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCharacters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchCharacters();
      setCharacters(data);
    } catch (err: any) {
      setError(err.message || "加载角色失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCharacters();
  }, [loadCharacters]);

  const createCharacter = useCallback(
    async (data: CharacterCreate) => {
      try {
        const newCharacter = await apiCreateCharacter(data);
        setCharacters((prev) => [newCharacter, ...prev]);
        return newCharacter;
      } catch (err: any) {
        setError(err.message || "创建角色失败");
        throw err;
      }
    },
    []
  );

  const updateCharacter = useCallback(
    async (id: string, data: Partial<CharacterCreate>) => {
      try {
        const updated = await apiUpdateCharacter(id, data);
        setCharacters((prev) =>
          prev.map((c) => (c.id === id ? updated : c))
        );
        return updated;
      } catch (err: any) {
        setError(err.message || "更新角色失败");
        throw err;
      }
    },
    []
  );

  const deleteCharacter = useCallback(async (id: string) => {
    try {
      await apiDeleteCharacter(id);
      setCharacters((prev) => prev.filter((c) => c.id !== id));
    } catch (err: any) {
      setError(err.message || "删除角色失败");
      throw err;
    }
  }, []);

  return {
    characters,
    loading,
    error,
    createCharacter,
    updateCharacter,
    deleteCharacter,
    refresh: loadCharacters,
  };
};
