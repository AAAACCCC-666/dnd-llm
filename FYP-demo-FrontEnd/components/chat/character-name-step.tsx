import * as React from "react";
import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle } from "lucide-react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

interface CharacterNameStepProps {
  name: string;
  setName: (name: string) => void;
  isMale: boolean | undefined;
  setIsMale: (isMale: boolean) => void;
  onNext: () => void;
  error: string | null;
}

export function CharacterNameStep({
  name,
  setName,
  isMale,
  setIsMale,
  onNext,
  error,
}: CharacterNameStepProps) {
  const [formError, setFormError] = useState<string | null>(null);

  const handleNext = () => {
    setFormError(null);

    if (!name.trim()) {
      setFormError("Character name is required.");
      return;
    }
    if (isMale === undefined) {
      setFormError("Please select gender.");
      return;
    }

    onNext();
  };

  return (
    <div className="p-6 max-w-lg mx-auto h-full overflow-y-auto">
      <Alert variant="default" className="mb-6">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Create Character - Step 1/3</AlertTitle>
        <AlertDescription>
          Please choose a name and gender for your character.
        </AlertDescription>
      </Alert>

      <div className="space-y-6">
        <div>
          <Label htmlFor="character-name">Character Name</Label>
          <Input
            id="character-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Eldrian Moonspeak"
            required
          />
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

        <Button onClick={handleNext} className="w-full">
          Next: Choose Race and Attributes
        </Button>
      </div>
    </div>
  );
}