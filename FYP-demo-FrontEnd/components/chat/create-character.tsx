import * as React from "react";
import { useState, useEffect } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertCircle, Loader2, Dice5 } from "lucide-react";
import { DndDataResponse, CharacterCreationFormData } from "@/app/chat/[session_id]/page";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { DiceRoller, type DiceRollResult } from "./dice-roller";

interface CharacterMissingNoticeProps {
  sessionId: string;
  dndData: DndDataResponse | null;
  onSubmit: (formData: CharacterCreationFormData) => Promise<void>;
  isCreating: boolean;
  error: string | null;
}

export function CharacterMissingNotice({
  dndData,
  onSubmit,
  isCreating,
  error,
}: CharacterMissingNoticeProps) {
  const [name, setName] = useState("");
  const [raceId, setRaceId] = useState<string>("");
  const [classId, setClassId] = useState<string>("");
  const [strength, setStrength] = useState<string>("10");
  const [dexterity, setDexterity] = useState<string>("10");
  const [constitution, setConstitution] = useState<string>("10");
  const [intelligence, setIntelligence] = useState<string>("10");
  const [wisdom, setWisdom] = useState<string>("10");
  const [charisma, setCharisma] = useState<string>("10");
  const [selectedProficiencies, setSelectedProficiencies] = useState<string[]>([]);
  const [isMale, setIsMale] = useState<boolean | undefined>(undefined);

  const [formError, setFormError] = useState<string | null>(null);
  const [showDiceRoller, setShowDiceRoller] = useState(false);
  const [lastRollResult, setLastRollResult] = useState<DiceRollResult | null>(null);

  // Reset form when dndData is available, to pick default values if any
  useEffect(() => {
    if (dndData?.races && Object.keys(dndData.races).length > 0) {
      // setRaceId(Object.keys(dndData.races)[0]); // Optionally set a default
    }
    if (dndData?.classes && Object.keys(dndData.classes).length > 0) {
      // setClassId(Object.keys(dndData.classes)[0]); // Optionally set a default
    }
    setSelectedProficiencies([]); // Reset proficiencies
  }, [dndData]);

  const handleDiceRollComplete = (result: DiceRollResult) => {
    setLastRollResult(result);
    // Auto-fill the corresponding ability score
    const attributeMap: { [key: string]: (value: string) => void } = {
      STR: setStrength,
      DEX: setDexterity,
      CON: setConstitution,
      INT: setIntelligence,
      WIS: setWisdom,
      CHA: setCharisma
    };

    const setter = attributeMap[result.attribute];
    if (setter) {
      setter(result.total.toString());
    }
  };


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError("Character name is required.");
      return;
    }
    if (!raceId) {
      setFormError("Please select a race.");
      return;
    }
    if (!classId) {
      setFormError("Please select a class.");
      return;
    }
    if (selectedProficiencies.length === 0) {
      setFormError("Please select at least one proficiency.");
      // Allow 0 proficiencies if desired by design
    }
    if (isMale === undefined) {
      setFormError("Please select a gender.");
      return;
    }

    const formData: CharacterCreationFormData = {
      name: name.trim(),
      race_id: parseInt(raceId, 10),
      class_id: parseInt(classId, 10),
      strength: parseInt(strength, 10) || 10,
      dexterity: parseInt(dexterity, 10) || 10,
      constitution: parseInt(constitution, 10) || 10,
      intelligence: parseInt(intelligence, 10) || 10,
      wisdom: parseInt(wisdom, 10) || 10,
      charisma: parseInt(charisma, 10) || 10,
      proficiency_ids: selectedProficiencies.map(id => parseInt(id, 10)),
      spell_ids: [],
      is_male: isMale,
    };
    await onSubmit(formData);
  };

  const handleProficiencyChange = (proficiencyId: string) => {
    setSelectedProficiencies(prev =>
      prev.includes(proficiencyId)
        ? prev.filter(id => id !== proficiencyId)
        : [...prev, proficiencyId]
    );
  };

  if (!dndData) {
    return (
      <Alert variant="default" className="m-6">
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        <AlertTitle>Loading Character Options...</AlertTitle>
        <AlertDescription>
          Please wait while we fetch the necessary data to create a character.
          {error && <p className="text-red-500 mt-2">{error}</p>}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="p-6 max-w-lg mx-auto">
      <Alert variant="default" className="mb-6">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Main Character Required</AlertTitle>
        <AlertDescription>
          A main character is required for this chat session. Please create one below.
        </AlertDescription>
      </Alert>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <Label htmlFor="character-name">Character Name</Label>
          <Input
            id="character-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Eldrin Moonwhisper"
            required
          />
        </div>

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

        <div>
          <Label>Gender</Label>
          <RadioGroup
            value={isMale === undefined ? "" : (isMale ? "male" : "female")}
            onValueChange={(value) => setIsMale(value === "male")}
            className="flex items-center space-x-4 mt-2"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="male" id="male" />
              <Label htmlFor="male">Male</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="female" id="female" />
              <Label htmlFor="female">Female</Label>
            </div>
          </RadioGroup>
        </div>

        <fieldset className="space-y-2">
          <div className="flex items-center justify-between">
            <legend className="text-sm font-medium">Ability Scores (Default 10)</legend>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowDiceRoller(!showDiceRoller)}
              className="flex items-center gap-2"
            >
              <Dice5 className="h-4 w-4" />
              {showDiceRoller ? "Hide" : "Show"} Dice Roller
            </Button>
          </div>

          {showDiceRoller && (
            <div className="mb-4">
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
                onRollComplete={handleDiceRollComplete}
              />
            </div>
          )}

          {lastRollResult && (
            <Alert className="mb-4">
              <AlertDescription>
                <div className="space-y-1">
                  <p className="font-medium">Last Roll Result:</p>
                  <p className="text-sm">
                    {lastRollResult.diceResults.join(", ")} →
                    Base {lastRollResult.baseSum} + {lastRollResult.race} bonus to {lastRollResult.attribute} {lastRollResult.bonus} =
                    Total {lastRollResult.total}
                  </p>
                </div>
              </AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="strength">Strength</Label>
              <Input id="strength" type="number" value={strength} onChange={e => setStrength(e.target.value)} min="3" max="20" />
            </div>
            <div>
              <Label htmlFor="dexterity">Dexterity</Label>
              <Input id="dexterity" type="number" value={dexterity} onChange={e => setDexterity(e.target.value)} min="3" max="20" />
            </div>
            <div>
              <Label htmlFor="constitution">Constitution</Label>
              <Input id="constitution" type="number" value={constitution} onChange={e => setConstitution(e.target.value)} min="3" max="20" />
            </div>
            <div>
              <Label htmlFor="intelligence">Intelligence</Label>
              <Input id="intelligence" type="number" value={intelligence} onChange={e => setIntelligence(e.target.value)} min="3" max="20" />
            </div>
            <div>
              <Label htmlFor="wisdom">Wisdom</Label>
              <Input id="wisdom" type="number" value={wisdom} onChange={e => setWisdom(e.target.value)} min="3" max="20" />
            </div>
            <div>
              <Label htmlFor="charisma">Charisma</Label>
              <Input id="charisma" type="number" value={charisma} onChange={e => setCharisma(e.target.value)} min="3" max="20" />
            </div>
          </div>
        </fieldset>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Proficiencies (Select at least one)</legend>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-60 overflow-y-auto p-2 border rounded bg-background">
            {Object.entries(dndData.proficiencies).map(([id, profName]) => (
              <div key={id} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id={`prof-${id}`}
                  value={id}
                  checked={selectedProficiencies.includes(id)}
                  onChange={() => handleProficiencyChange(id)}
                  className="form-checkbox h-4 w-4 text-blue-600 transition duration-150 ease-in-out"
                />
                <Label htmlFor={`prof-${id}`} className="text-sm font-normal">{profName}</Label>
              </div>
            ))}
          </div>
        </fieldset>

        {formError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Validation Error</AlertTitle>
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}

        {error && ( // Display error from API call
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Creation Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" disabled={isCreating} className="w-full">
          {isCreating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating Character...
            </>
          ) : (
            "Create Character"
          )}
        </Button>
      </form>
    </div>
  );
}
