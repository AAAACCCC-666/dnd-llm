import * as React from "react";
import { useState, useEffect } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { AlertCircle, Loader2 } from "lucide-react";
import { DndDataResponse, CharacterCreationFormData } from "@/app/chat/[session_id]/page";

interface CharacterSpellsStepProps {
  dndData: DndDataResponse;
  raceId: string;
  classId: string;
  selectedSpells: string[];
  setSelectedSpells: React.Dispatch<React.SetStateAction<string[]>>;
  onPrevious: () => void;
  onSubmit: (formData: CharacterCreationFormData) => Promise<void>;
  isCreating: boolean;
  name: string;
  strength: string;
  dexterity: string;
  constitution: string;
  intelligence: string;
  wisdom: string;
  charisma: string;
  isMale: boolean;
  error: string | null;
}

// 根据职业和种族获取可用法术
const getAvailableSpells = (
  dndData: DndDataResponse,
  raceId: string,
  classId: string,
  intelligence: string,
  wisdom: string,
  charisma: string
): string[] => {
  if (!dndData?.spells) return [];

  let availableSpells = Object.keys(dndData.spells);

  // 职业法术限制
  const classSpellRestrictions: { [key: string]: string[] } = {
    "2": [], // 法师 - 可以学习所有法术
    "3": ["Healing Word", "Cure Wounds", "Bless", "Shield of Faith"], // 牧师 - 治疗和防护法术
    "4": ["Hunter's Mark", "Goodberry", "Speak with Animals", "Pass without Trace"], // 游侠 - 自然和追踪法术
    "6": ["Divine Favor", "Cure Wounds", "Bless", "Shield of Faith"], // 圣骑士 - 神圣和防护法术
    "7": [], // 术士 - 可以学习所有法术
    "8": ["Goodberry", "Entangle", "Animal Friendship", "Speak with Animals"], // 德鲁伊 - 自然和变形法术
    "9": [], // 吟游诗人 - 可以学习所有法术
  };

  // 非施法职业
  const nonSpellcastingClasses = ["1", "5"]; // 战士、盗贼
  if (nonSpellcastingClasses.includes(classId)) {
    return [];
  }

  // 应用职业法术限制
  if (classSpellRestrictions[classId]) {
    availableSpells = availableSpells.filter(spellId => 
      classSpellRestrictions[classId].includes(dndData.spells[spellId])
    );
  }

  // 种族法术偏好
  const raceSpellPreferences: { [key: string]: { include: string[], exclude: string[] } } = {
    "2": { // 精灵
      include: ["Goodberry", "Entangle", "Faerie Fire", "Invisibility"],
      exclude: ["Inflict Wounds", "Blight", "Bestow Curse"]
    },
    "3": { // 矮人
      include: ["Shield of Faith", "Protection from Evil and Good", "Stone Shape"],
      exclude: []
    },
    "4": { // 半身人
      include: ["Invisibility", "Silent Image", "Pass without Trace"],
      exclude: []
    },
    "6": { // 半兽人
      include: ["Enhance Ability", "Heroism", "Haste"],
      exclude: []
    },
    "7": { // 龙裔
      include: ["Burning Hands", "Fireball", "Dragon's Breath"],
      exclude: []
    },
    "8": { // 提夫林
      include: ["Hellish Rebuke", "Darkness", "Fireball"],
      exclude: []
    },
    "9": { // 侏儒
      include: ["Minor Illusion", "Silent Image", "Fabricate"],
      exclude: []
    }
  };

  // 应用种族法术偏好
  if (raceSpellPreferences[raceId]) {
    const { include, exclude } = raceSpellPreferences[raceId];
    
    // 优先包含种族偏好的法术
    const preferredSpells = availableSpells.filter(spellId => 
      include.includes(dndData.spells[spellId])
    );
    
    // 排除种族不喜欢的法术
    availableSpells = availableSpells.filter(spellId => 
      !exclude.includes(dndData.spells[spellId])
    );

    // 将偏好的法术放在前面
    availableSpells = [...preferredSpells, ...availableSpells.filter(spellId => !preferredSpells.includes(spellId))];
  }

  // 根据属性值限制法术数量
  const intScore = parseInt(intelligence, 10) || 10;
  const wisScore = parseInt(wisdom, 10) || 10;
  const chaScore = parseInt(charisma, 10) || 10;

  // 施法职业需要相应的属性达到一定值
  const spellcastingClasses = ["2", "3", "4", "6", "7", "8", "9"]; // 法师、牧师、游侠、圣骑士、术士、德鲁伊、吟游诗人
  if (spellcastingClasses.includes(classId)) {
    const requiredScore = 13;
    let hasRequiredAttribute = false;

    if (classId === "2" && intScore >= requiredScore) hasRequiredAttribute = true; // 法师 - 智力
    if (classId === "3" && wisScore >= requiredScore) hasRequiredAttribute = true; // 牧师 - 感知
    if (classId === "4" && wisScore >= requiredScore) hasRequiredAttribute = true; // 游侠 - 感知
    if (classId === "6" && chaScore >= requiredScore) hasRequiredAttribute = true; // 圣骑士 - 魅力
    if (classId === "7" && chaScore >= requiredScore) hasRequiredAttribute = true; // 术士 - 魅力
    if (classId === "8" && wisScore >= requiredScore) hasRequiredAttribute = true; // 德鲁伊 - 感知
    if (classId === "9" && chaScore >= requiredScore) hasRequiredAttribute = true; // 吟游诗人 - 魅力

    if (!hasRequiredAttribute) {
      availableSpells = []; // 属性不足，无法施法
    }
  }

  return availableSpells;
};

export function CharacterSpellsStep({
  dndData,
  raceId,
  classId,
  selectedSpells,
  setSelectedSpells,
  onPrevious,
  onSubmit,
  isCreating,
  name,
  strength,
  dexterity,
  constitution,
  intelligence,
  wisdom,
  charisma,
  isMale,
  error,
}: CharacterSpellsStepProps) {
  const [formError, setFormError] = useState<string | null>(null);
  const [availableSpells, setAvailableSpells] = useState<string[]>([]);

  useEffect(() => {
    const spells = getAvailableSpells(
      dndData,
      raceId,
      classId,
      intelligence,
      wisdom,
      charisma
    );
    setAvailableSpells(spells);
    
    // 清除不可用的已选法术
    setSelectedSpells(prev => prev.filter(spellId => spells.includes(spellId)));
  }, [dndData, raceId, classId, intelligence, wisdom, charisma, setSelectedSpells]);

  const handleSpellChange = (spellId: string) => {
    setSelectedSpells((prev: string[]) =>
      prev.includes(spellId)
        ? prev.filter((id: string) => id !== spellId)
        : [...prev, spellId]
    );
  };

  const handleSubmit = async () => {
    setFormError(null);

    // 非施法职业不需要选择法术
    const nonSpellcastingClasses = ["1", "5"]; // 战士、盗贼
    if (nonSpellcastingClasses.includes(classId)) {
      await submitForm();
      return;
    }

    // 施法职业需要至少选择一个法术
    if (selectedSpells.length === 0 && availableSpells.length > 0) {
      setFormError("Please select at least one spell.");
      return;
    }

    await submitForm();
  };

  const submitForm = async () => {
    const formData = {
      name: name.trim(),
      race_id: parseInt(raceId, 10),
      class_id: parseInt(classId, 10),
      strength: parseInt(strength, 10) || 10,
      dexterity: parseInt(dexterity, 10) || 10,
      constitution: parseInt(constitution, 10) || 10,
      intelligence: parseInt(intelligence, 10) || 10,
      wisdom: parseInt(wisdom, 10) || 10,
      charisma: parseInt(charisma, 10) || 10,
      proficiency_ids: [], // 将在熟练项步骤中设置
      spell_ids: selectedSpells.map(id => parseInt(id, 10)),
      is_male: isMale,
    };

    await onSubmit(formData);
  };

  const getSpellRestrictionMessage = () => {
    const nonSpellcastingClasses = ["1", "5"]; // 战士、盗贼
    if (nonSpellcastingClasses.includes(classId)) {
      return "Your class cannot cast spells.";
    }

    if (availableSpells.length === 0) {
      return "No spells available for your current race, class, and attribute combination.";
    }

    const maxSpells = Math.min(3, availableSpells.length);
    return `Select up to ${maxSpells} spells from the available options.`;
  };

  return (
    <div className="p-6 max-w-lg mx-auto h-full overflow-y-auto">
      <Alert variant="default" className="mb-6">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Create Character - Step 4/4</AlertTitle>
        <AlertDescription>
          Select your starting spells based on your race and class.
        </AlertDescription>
      </Alert>

      <div className="space-y-6">
        <div className="bg-muted p-4 rounded-lg">
          <h4 className="font-medium mb-2">Spell Restrictions</h4>
          <p className="text-sm">{getSpellRestrictionMessage()}</p>
        </div>

        {availableSpells.length > 0 && (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Available Spells</legend>
            <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto p-2 border rounded">
              {availableSpells.map((spellId) => (
               <div key={spellId} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id={`spell-${spellId}`}
                    value={spellId}
                    checked={selectedSpells.includes(spellId)}
                    onChange={() => handleSpellChange(spellId)}
                    disabled={selectedSpells.length >= 3 && !selectedSpells.includes(spellId)}
                    className="form-checkbox h-4 w-4 text-blue-600 transition duration-150 ease-in-out"
                  />
                  <Label htmlFor={`spell-${spellId}`} className="text-sm font-normal">
                    {dndData.spells[spellId]}
                  </Label>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Selected: {selectedSpells.length}/3
            </p>
          </fieldset>
        )}

        <div className="bg-muted p-4 rounded-lg">
          <h4 className="font-medium mb-2">Character Summary</h4>
          <div className="text-sm space-y-1">
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Race:</strong> {dndData.races[raceId]}</p>
            <p><strong>Class:</strong> {dndData.classes[classId]}</p>
            <p><strong>Gender:</strong> {isMale ? 'Male' : 'Female'}</p>
            <p><strong>Attributes:</strong> Strength {strength}, Dexterity {dexterity}, Constitution {constitution}, Intelligence {intelligence}, Wisdom {wisdom}, Charisma {charisma}</p>
            <p><strong>Spells Selected:</strong> {selectedSpells.length}</p>
          </div>
        </div>

        {formError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Validation Error</AlertTitle>
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Creation Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex gap-4">
          <Button variant="outline" onClick={onPrevious} className="flex-1" disabled={isCreating}>
            Previous: Proficiencies
          </Button>
          <Button onClick={handleSubmit} disabled={isCreating} className="flex-1">
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Character...
              </>
            ) : (
              "Create Character"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}