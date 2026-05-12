import * as React from "react";
import { useState, useEffect } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";
import { DndDataResponse, CharacterCreationFormData } from "@/app/chat/[session_id]/page";
import { CharacterNameStep } from "./character-name-step";
import { CharacterRaceAttributesStep } from "./character-race-attributes-step";
import { CharacterProficienciesStep } from "./character-proficiencies-step";
import { CharacterSpellsStep } from "./character-spells-step";

interface CharacterMissingNoticeProps {
  sessionId: string;
  dndData: DndDataResponse | null;
  onSubmit: (formData: CharacterCreationFormData) => Promise<void>;
  isCreating: boolean;
  error: string | null;
}

type Step = "name" | "race-attributes" | "proficiencies" | "spells";

export function CharacterMissingNotice({
  dndData,
  onSubmit,
  isCreating,
  error,
}: CharacterMissingNoticeProps) {
  const [currentStep, setCurrentStep] = useState<Step>("name");

  // Form state
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
  const [selectedSpells, setSelectedSpells] = useState<string[]>([]);
  const [isMale, setIsMale] = useState<boolean | undefined>(undefined);

  // Reset form when dndData is available, to pick default values if any
  useEffect(() => {
    if (dndData?.races && Object.keys(dndData.races).length > 0) {
      // Optionally set a default race
    }
    if (dndData?.classes && Object.keys(dndData.classes).length > 0) {
      // Optionally set a default class
    }
    setSelectedProficiencies([]); // Reset proficiencies
  }, [dndData]);

  const handleNextStep = () => {
    switch (currentStep) {
      case "name":
        setCurrentStep("race-attributes");
        break;
      case "race-attributes":
        setCurrentStep("proficiencies");
        break;
      case "proficiencies":
        setCurrentStep("spells");
        break;
    }
  };

  const handlePreviousStep = () => {
    switch (currentStep) {
      case "race-attributes":
        setCurrentStep("name");
        break;
      case "proficiencies":
        setCurrentStep("race-attributes");
        break;
      case "spells":
        setCurrentStep("proficiencies");
        break;
    }
  };

  const handleSubmit = async (formData: any) => {
    // 合并熟练项和法术数据
    const finalFormData = {
      ...formData,
      proficiency_ids: selectedProficiencies.map(id => parseInt(id, 10)),
    };
    await onSubmit(finalFormData);
  };

  if (!dndData) {
    return (
      <Alert variant="default" className="m-6">
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        <AlertTitle>Loading character options...</AlertTitle>
        <AlertDescription>
          Please wait while we fetch the data needed to create your character.
          {error && <p className="text-red-500 mt-2">{error}</p>}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="h-full">
      {currentStep === "name" && (
        <CharacterNameStep
          name={name}
          setName={setName}
          isMale={isMale}
          setIsMale={setIsMale}
          onNext={handleNextStep}
          error={error}
        />
      )}

      {currentStep === "race-attributes" && (
        <CharacterRaceAttributesStep
          dndData={dndData}
          raceId={raceId}
          setRaceId={setRaceId}
          classId={classId}
          setClassId={setClassId}
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
          onPrevious={handlePreviousStep}
          onNext={handleNextStep}
          error={error}
        />
      )}

      {currentStep === "proficiencies" && (
        <CharacterProficienciesStep
          dndData={dndData}
          selectedProficiencies={selectedProficiencies}
          setSelectedProficiencies={setSelectedProficiencies}
          onPrevious={handlePreviousStep}
          onNext={handleNextStep}
          name={name}
          raceId={raceId}
          classId={classId}
          strength={strength}
          dexterity={dexterity}
          constitution={constitution}
          intelligence={intelligence}
          wisdom={wisdom}
          charisma={charisma}
          isMale={isMale as boolean}
          error={error}
        />
      )}

      {currentStep === "spells" && (
        <CharacterSpellsStep
          dndData={dndData}
          raceId={raceId}
          classId={classId}
          selectedSpells={selectedSpells}
          setSelectedSpells={setSelectedSpells}
          onPrevious={handlePreviousStep}
          onSubmit={handleSubmit}
          isCreating={isCreating}
          name={name}
          strength={strength}
          dexterity={dexterity}
          constitution={constitution}
          intelligence={intelligence}
          wisdom={wisdom}
          charisma={charisma}
          isMale={isMale as boolean}
          error={error}
        />
      )}
    </div>
  );
}