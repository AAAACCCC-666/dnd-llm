"use client";

import * as React from "react";
import { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, User, Shield, Zap, Brain, Heart, RefreshCw } from "lucide-react";
import { buildApiUrl } from "@/lib/api";

interface CharacterInfo {
  id: string;
  name: string;
  race?: string;
  race_id?: number;
  class?: string;
  class_id?: number;
  level?: number;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  health?: number;  // Backend actual attribute name
  temp_health?: number;
  armor?: number;   // Backend actual attribute name
  speed?: number;
  experience?: number;
  gold?: number;
  proficiencies?: string[];
  is_male: boolean;
}

interface CharacterInfoProps {
  sessionId: string;
  refreshToken?: number;
  onClearHighlights?: () => void;
}

interface SessionCharacter {
  id: string;
  name: string;
}

interface DndData {
  races: { [id: string]: string };
  classes: { [id: string]: string };
  proficiencies: { [id: string]: string };
}

export const CharacterInfo = forwardRef<{ clearHighlights: () => void }, CharacterInfoProps>(({ sessionId, refreshToken }, ref) => {
  useImperativeHandle(ref, () => ({
    clearHighlights: () => {
      setHighlightedAttributes(new Set());
    }
  }));
  const [character, setCharacter] = useState<CharacterInfo | null>(null);
  const [dndData, setDndData] = useState<DndData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [highlightedAttributes, setHighlightedAttributes] = useState<Set<string>>(new Set());
  const [previousCharacter, setPreviousCharacter] = useState<CharacterInfo | null>(null);

  const fetchCharacterInfo = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      // First get the list of characters associated with the session
      const sessionCharactersUrl = buildApiUrl(`/characters/session/${sessionId}`);
      const sessionResponse = await fetch(sessionCharactersUrl);

      if (!sessionResponse.ok) {
        throw new Error(`Failed to fetch session characters: ${sessionResponse.statusText}`);
      }

      const characters: SessionCharacter[] = await sessionResponse.json();

      if (characters.length === 0) {
        setCharacter(null);
        setLastUpdated(new Date());
        return;
      }

      // Assume the first character is the main character
      const mainCharacter = characters[0];

      // Get detailed information through character ID
      const characterDetailUrl = buildApiUrl(`/characters/id/${encodeURIComponent(mainCharacter.id)}`);
      const detailResponse = await fetch(characterDetailUrl);

      if (!detailResponse.ok) {
        throw new Error(`Failed to fetch character details: ${detailResponse.statusText}`);
      }

      const characterData = await detailResponse.json();
      console.log("Character API Response:", characterData); // Debug information
      
      // Detect attribute changes (only when we have previous character data)
      if (previousCharacter) {
        const changedAttributes = new Set<string>();
        
        // Check numeric attributes
        const numericAttributes = [
          'strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma',
          'health', 'temp_health', 'armor', 'speed', 'experience', 'gold', 'level'
        ];
        
        numericAttributes.forEach(attr => {
          const currentValue = characterData[attr as keyof CharacterInfo];
          const previousValue = previousCharacter[attr as keyof CharacterInfo];
          if (currentValue !== previousValue) {
            changedAttributes.add(attr);
          }
        });
        
        // Check string attributes
        const stringAttributes = ['name', 'race', 'class'];
        stringAttributes.forEach(attr => {
          const currentValue = characterData[attr as keyof CharacterInfo];
          const previousValue = previousCharacter[attr as keyof CharacterInfo];
          if (currentValue !== previousValue) {
            changedAttributes.add(attr);
          }
        });
        
        // Check boolean attributes
        const booleanAttributes = ['is_male'];
        booleanAttributes.forEach(attr => {
          const currentValue = characterData[attr as keyof CharacterInfo];
          const previousValue = previousCharacter[attr as keyof CharacterInfo];
          if (currentValue !== previousValue) {
            changedAttributes.add(attr);
          }
        });
        
        // Check array attributes
        if (JSON.stringify(characterData.proficiencies) !== JSON.stringify(previousCharacter.proficiencies)) {
          changedAttributes.add('proficiencies');
        }
        
        setHighlightedAttributes(changedAttributes);
      }
      
      setPreviousCharacter(character);
      setCharacter(characterData);
      setLastUpdated(new Date());
    } catch (err) {
      const errMessage = err instanceof Error ? err.message : "An unknown error occurred.";
      setError(errMessage);
      console.error("Error fetching character info:", err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleRefresh = () => {
    fetchCharacterInfo();
  };

  // Clear highlighted attributes when user sends a message (new conversation turn)
  const clearHighlights = () => {
    setHighlightedAttributes(new Set());
  };

  useEffect(() => {
    const fetchDndData = async () => {
      try {
        const response = await fetch(buildApiUrl("/characters/dnd-data"));
        if (response.ok) {
          const data = await response.json();
          setDndData(data);
        }
      } catch (err) {
        console.error("Error fetching D&D data:", err);
      }
    };

    fetchDndData();
  }, []);

  useEffect(() => {
    fetchCharacterInfo();
  }, [fetchCharacterInfo, refreshToken]);

  const getRaceName = (raceId?: number): string => {
    if (!raceId || !dndData) return "Unknown";
    return dndData.races[raceId.toString()] || `Race ID: ${raceId}`;
  };

  const getClassName = (classId?: number): string => {
    if (!classId || !dndData) return "Unknown";
    return dndData.classes[classId.toString()] || `Class ID: ${classId}`;
  };

  const getAbilityModifier = (score: number): string => {
    const modifier = Math.floor((score - 10) / 2);
    return modifier >= 0 ? `+${modifier}` : `${modifier}`;
  };

  const getProficiencyBonus = (level: number): number => {
    return Math.floor((level - 1) / 4) + 2;
  };

  // Get highlight class for attribute
  const getHighlightClass = (attribute: string): string => {
    return highlightedAttributes.has(attribute)
      ? "bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-400 rounded px-1"
      : "";
  };

  if (loading) {
    return (
      <div className="w-full bg-card rounded-lg border shadow-sm p-4">
        <div className="flex items-center gap-2 mb-4">
          <User className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Character Info</h3>
        </div>
        <div className="space-y-4">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-20 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full bg-card rounded-lg border shadow-sm p-4">
        <div className="flex items-center gap-2 mb-4">
          <User className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Character Info</h3>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!character) {
    return (
      <div className="w-full bg-card rounded-lg border shadow-sm p-4">
        <div className="flex items-center gap-2 mb-4">
          <User className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Character Info</h3>
        </div>
        <p className="text-sm text-muted-foreground text-center py-4">
          No character information available
        </p>
      </div>
    );
  }

  return (
    <div className="w-full bg-card rounded-lg border shadow-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <User className="h-5 w-5" />
          <h3 className="text-lg font-semibold">{character.name}</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded-full">
            Lv.{character.level || 1}
          </span>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-1.5 rounded-md hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Refresh character info"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>
      <div className="space-y-4">
        {/* Basic Info */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="p-2 rounded">
            <span className="text-muted-foreground">Race:</span>
            <div className={`font-medium transition-all ${getHighlightClass('race')}`}>
              {character.race || getRaceName(character.race_id)}
            </div>
          </div>
          <div className="p-2 rounded">
            <span className="text-muted-foreground">Class:</span>
            <div className={`font-medium transition-all ${getHighlightClass('class')}`}>
              {character.class || getClassName(character.class_id)}
            </div>
          </div>
          <div className="p-2 rounded">
            <span className="text-muted-foreground">Gender:</span>
            <div className={`font-medium transition-all ${getHighlightClass('is_male')}`}>
              {character.is_male ? "Male" : "Female"}
            </div>
          </div>
          <div className="p-2 rounded">
            <span className="text-muted-foreground">Proficiency:</span>
            <div className={`font-medium transition-all ${getHighlightClass('level')}`}>
              +{getProficiencyBonus(character.level || 1)}
            </div>
          </div>
        </div>

        {/* HP and AC */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2 p-2 bg-red-100 dark:bg-red-900/20 rounded-lg">
            <Heart className="h-4 w-4 text-red-600 dark:text-red-400" />
            <div>
              <div className="text-xs text-muted-foreground">Hit Points</div>
              <div className={`font-bold text-red-700 dark:text-red-300 transition-all ${getHighlightClass('health')}`}>
                {character.health || "Unknown"}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
            <Shield className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <div>
              <div className="text-xs text-muted-foreground">Armor Class</div>
              <div className={`font-bold text-blue-700 dark:text-blue-300 transition-all ${getHighlightClass('armor')}`}>
                {character.armor || "Unknown"}
              </div>
            </div>
          </div>
        </div>

        {/* Ability Scores */}
        <div>
          <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Ability Scores
          </h4>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center p-2 bg-muted rounded">
              <div className={`font-bold transition-all ${getHighlightClass('strength')}`}>{character.strength}</div>
              <div className="text-muted-foreground">STR</div>
              <div className="text-xs">{getAbilityModifier(character.strength)}</div>
            </div>
            <div className="text-center p-2 bg-muted rounded">
              <div className={`font-bold transition-all ${getHighlightClass('dexterity')}`}>{character.dexterity}</div>
              <div className="text-muted-foreground">DEX</div>
              <div className="text-xs">{getAbilityModifier(character.dexterity)}</div>
            </div>
            <div className="text-center p-2 bg-muted rounded">
              <div className={`font-bold transition-all ${getHighlightClass('constitution')}`}>{character.constitution}</div>
              <div className="text-muted-foreground">CON</div>
              <div className="text-xs">{getAbilityModifier(character.constitution)}</div>
            </div>
            <div className="text-center p-2 bg-muted rounded">
              <div className={`font-bold transition-all ${getHighlightClass('intelligence')}`}>{character.intelligence}</div>
              <div className="text-muted-foreground">INT</div>
              <div className="text-xs">{getAbilityModifier(character.intelligence)}</div>
            </div>
            <div className="text-center p-2 bg-muted rounded">
              <div className={`font-bold transition-all ${getHighlightClass('wisdom')}`}>{character.wisdom}</div>
              <div className="text-muted-foreground">WIS</div>
              <div className="text-xs">{getAbilityModifier(character.wisdom)}</div>
            </div>
            <div className="text-center p-2 bg-muted rounded">
              <div className={`font-bold transition-all ${getHighlightClass('charisma')}`}>{character.charisma}</div>
              <div className="text-muted-foreground">CHA</div>
              <div className="text-xs">{getAbilityModifier(character.charisma)}</div>
            </div>
          </div>
        </div>

        {/* Proficiencies */}
        {character.proficiencies && character.proficiencies.length > 0 && (
          <div>
            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
              <Brain className="h-4 w-4" />
              Proficiencies
            </h4>
            <div className={`flex flex-wrap gap-1 transition-all ${getHighlightClass('proficiencies')}`}>
              {character.proficiencies.map((prof, index) => (
                <span
                  key={index}
                  className="px-2 py-1 text-xs border border-border rounded-md bg-muted"
                >
                  {prof}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Last Updated */}
        {/* Removed bottom timestamp, relies on parent refresh */}
      </div>
    </div>
  );
});
