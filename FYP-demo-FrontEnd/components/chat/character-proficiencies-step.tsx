import * as React from "react";
import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { AlertCircle } from "lucide-react";
import { DndDataResponse } from "@/app/chat/[session_id]/page";

interface CharacterProficienciesStepProps {
  dndData: DndDataResponse;
  selectedProficiencies: string[];
  setSelectedProficiencies: React.Dispatch<React.SetStateAction<string[]>>;
  onPrevious: () => void;
  onNext: () => void;
  name: string;
  raceId: string;
  classId: string;
  strength: string;
  dexterity: string;
  constitution: string;
  intelligence: string;
  wisdom: string;
  charisma: string;
  isMale: boolean;
  error: string | null;
}

export function CharacterProficienciesStep({
  dndData,
  selectedProficiencies,
  setSelectedProficiencies,
  onPrevious,
  onNext,
  name,
  raceId,
  classId,
  strength,
  dexterity,
  constitution,
  intelligence,
  wisdom,
  charisma,
  isMale,
  error,
}: CharacterProficienciesStepProps) {
  const [formError, setFormError] = useState<string | null>(null);

  const handleProficiencyChange = (proficiencyId: string) => {
    setSelectedProficiencies((prev: string[]) =>
      prev.includes(proficiencyId)
        ? prev.filter((id: string) => id !== proficiencyId)
        : [...prev, proficiencyId]
    );
  };

  const handleNext = () => {
    setFormError(null);

    if (selectedProficiencies.length === 0) {
      setFormError("Please select at least one proficiency.");
      return;
    }

    onNext();
  };

  return (
    <div className="p-6 max-w-lg mx-auto h-full overflow-y-auto">
      <Alert variant="default" className="mb-6">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Create Character - Step 3/4</AlertTitle>
        <AlertDescription>
          Please select your proficiencies. Choose at least one.
        </AlertDescription>
      </Alert>

      <div className="space-y-6">
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Proficiencies (Select at least one)</legend>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-60 overflow-y-auto p-2 border rounded">
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

        <div className="bg-muted p-4 rounded-lg">
          <h4 className="font-medium mb-2">Character Summary</h4>
          <div className="text-sm space-y-1">
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Race:</strong> {dndData.races[raceId]}</p>
            <p><strong>Class:</strong> {dndData.classes[classId]}</p>
            <p><strong>Gender:</strong> {isMale ? 'Male' : 'Female'}</p>
            <p><strong>Attributes:</strong> Strength {strength}, Dexterity {dexterity}, Constitution {constitution}, Intelligence {intelligence}, Wisdom {wisdom}, Charisma {charisma}</p>
            <p><strong>Proficiencies:</strong> {selectedProficiencies.length}</p>
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
          <Button variant="outline" onClick={onPrevious} className="flex-1">
            Previous: Race and Attributes
          </Button>
          <Button onClick={handleNext} className="flex-1">
            Next: Choose Spells
          </Button>
        </div>
      </div>
    </div>
  );
}