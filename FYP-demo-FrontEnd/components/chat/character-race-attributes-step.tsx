import * as React from "react";
import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertCircle } from "lucide-react";
import { DndDataResponse } from "@/app/chat/[session_id]/page";
import { Input } from "@/components/ui/input";
import { DiceRoller } from "./dice-roller";

interface CharacterRaceAttributesStepProps {
  dndData: DndDataResponse;
  raceId: string;
  setRaceId: (raceId: string) => void;
  classId: string;
  setClassId: (classId: string) => void;
  strength: string;
  setStrength: (strength: string) => void;
  dexterity: string;
  setDexterity: (dexterity: string) => void;
  constitution: string;
  setConstitution: (constitution: string) => void;
  intelligence: string;
  setIntelligence: (intelligence: string) => void;
  wisdom: string;
  setWisdom: (wisdom: string) => void;
  charisma: string;
  setCharisma: (charisma: string) => void;
  onPrevious: () => void;
  onNext: () => void;
  error: string | null;
}

export function CharacterRaceAttributesStep({
  dndData,
  raceId,
  setRaceId,
  classId,
  setClassId,
  strength,
  setStrength,
  dexterity,
  setDexterity,
  constitution,
  setConstitution,
  intelligence,
  setIntelligence,
  wisdom,
  setWisdom,
  charisma,
  setCharisma,
  onPrevious,
  onNext,
  error,
}: CharacterRaceAttributesStepProps) {
  const [formError, setFormError] = useState<string | null>(null);

  const handleNext = () => {
    setFormError(null);

    if (!raceId) {
      setFormError("Please select a race.");
      return;
    }
    if (!classId) {
      setFormError("Please select a class.");
      return;
    }

    // Validate ability scores
    const scores = [strength, dexterity, constitution, intelligence, wisdom, charisma];
    for (const score of scores) {
      const num = parseInt(score, 10);
      if (isNaN(num) || num < 3 || num > 20) {
        setFormError("All attribute values must be between 3 and 20. Please roll dice for all attributes or set them manually.");
        return;
      }
    }

    onNext();
  };

  return (
    <div className="p-6 w-full max-w-6xl mx-auto h-full overflow-y-auto">
      <Alert variant="default" className="mb-6">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Create Character - Step 2/3</AlertTitle>
        <AlertDescription>
          Please select your race, class, and attribute values.
        </AlertDescription>
      </Alert>

      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="race">Race</Label>
            <Select value={raceId} onValueChange={setRaceId} required>
              <SelectTrigger id="race">
                <SelectValue placeholder="Select a race" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(dndData.races).map(([id, raceName]) => (
                  <SelectItem key={id} value={id}>
                    {raceName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="class">Class</Label>
            <Select value={classId} onValueChange={setClassId} required>
              <SelectTrigger id="class">
                <SelectValue placeholder="Select a class" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(dndData.classes).map(([id, className]) => (
                  <SelectItem key={id} value={id}>
                    {className}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-6">
          {/* 掷骰子区域 */}
          <div className="border border-blue-200 dark:border-slate-700 rounded-lg p-4 bg-blue-50 dark:bg-slate-900/60">
            <h3 className="text-lg font-medium mb-3 text-gray-900 dark:text-gray-100">Roll Attributes with Dice</h3>
            <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">
              Use D&D standard method: Roll 5 dice, remove the lowest and highest values, sum the middle three, then add racial bonuses
            </p>
            <DiceRoller
              raceId={raceId}
              setRaceId={setRaceId}
              showRaceSelect={false}
              strength={strength}
              setStrength={setStrength}
              dexterity={dexterity}
              setDexterity={setDexterity}
              constitution={constitution}
              setConstitution={setConstitution}
              intelligence={intelligence}
              setIntelligence={setIntelligence}
              wisdom={wisdom}
              setWisdom={setWisdom}
              charisma={charisma}
              setCharisma={setCharisma}
            />
          </div>

          {/* 手动属性设置区域 */}
          <fieldset className="space-y-4">
            <legend className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Manual Attribute Settings (Default 10)</legend>
            <div className="grid grid-cols-6 gap-4">
              <div>
                <Label htmlFor="strength">Strength</Label>
                <Input
                  id="strength"
                  type="number"
                  value={strength}
                  onChange={e => setStrength(e.target.value)}
                  min="3"
                  max="20"
                />
              </div>
              <div>
                <Label htmlFor="dexterity">Dexterity</Label>
                <Input
                  id="dexterity"
                  type="number"
                  value={dexterity}
                  onChange={e => setDexterity(e.target.value)}
                  min="3"
                  max="20"
                />
              </div>
              <div>
                <Label htmlFor="constitution">Constitution</Label>
                <Input
                  id="constitution"
                  type="number"
                  value={constitution}
                  onChange={e => setConstitution(e.target.value)}
                  min="3"
                  max="20"
                />
              </div>
              <div>
                <Label htmlFor="intelligence">Intelligence</Label>
                <Input
                  id="intelligence"
                  type="number"
                  value={intelligence}
                  onChange={e => setIntelligence(e.target.value)}
                  min="3"
                  max="20"
                />
              </div>
              <div>
                <Label htmlFor="wisdom">Wisdom</Label>
                <Input
                  id="wisdom"
                  type="number"
                  value={wisdom}
                  onChange={e => setWisdom(e.target.value)}
                  min="3"
                  max="20"
                />
              </div>
              <div>
                <Label htmlFor="charisma">Charisma</Label>
                <Input
                  id="charisma"
                  type="number"
                  value={charisma}
                  onChange={e => setCharisma(e.target.value)}
                  min="3"
                  max="20"
                />
              </div>
            </div>
          </fieldset>
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
          <Button variant="outline" onClick={onPrevious} className="flex-1">
            Previous: Character Name
          </Button>
          <Button onClick={handleNext} className="flex-1">
            Next: Choose Proficiencies
          </Button>
        </div>
      </div>
    </div>
  );
}
