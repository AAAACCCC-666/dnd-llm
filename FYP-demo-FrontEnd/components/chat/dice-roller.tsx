"use client"

import * as React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export type DiceRollResult = {
  diceResults: number[]
  baseSum: number
  bonus: number
  total: number
  race: string
  attribute: Attribute
}

interface DiceRollerProps {
  raceId?: string
  setRaceId?: (raceId: string) => void
  showRaceSelect?: boolean
  strength?: string
  setStrength?: (strength: string) => void
  dexterity?: string
  setDexterity?: (dexterity: string) => void
  constitution?: string
  setConstitution?: (constitution: string) => void
  intelligence?: string
  setIntelligence?: (intelligence: string) => void
  wisdom?: string
  setWisdom?: (wisdom: string) => void
  charisma?: string
  setCharisma?: (charisma: string) => void
  onRollComplete?: (result: DiceRollResult) => void
}

type Attribute = "STR" | "DEX" | "CON" | "INT" | "WIS" | "CHA"
type RaceId = "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12" | "13" | "14" | "15" | "16"

interface RaceBonus {
  STR: number
  DEX: number
  CON: number
  INT: number
  WIS: number
  CHA: number
}

// D&D 5e PHB Racial Bonuses
const racialBonus: Record<RaceId, RaceBonus> = {
  "1": { STR: 1, DEX: 1, CON: 1, INT: 1, WIS: 1, CHA: 1 }, // Human
  "2": { STR: 0, DEX: 0, CON: 2, INT: 0, WIS: 0, CHA: 0 }, // Dwarf
  "3": { STR: 2, DEX: 0, CON: 2, INT: 0, WIS: 0, CHA: 0 }, // Hill Dwarf
  "4": { STR: 0, DEX: 2, CON: 0, INT: 0, WIS: 0, CHA: 0 }, // Elf
  "5": { STR: 0, DEX: 2, CON: 0, INT: 1, WIS: 0, CHA: 0 }, // High Elf
  "6": { STR: 0, DEX: 2, CON: 0, INT: 0, WIS: 1, CHA: 0 }, // Wood Elf
  "7": { STR: 0, DEX: 2, CON: 0, INT: 0, WIS: 0, CHA: 0 }, // Halfling
  "8": { STR: 0, DEX: 2, CON: 0, INT: 0, WIS: 0, CHA: 1 }, // Lightfoot Halfling
  "9": { STR: 0, DEX: 2, CON: 1, INT: 0, WIS: 0, CHA: 0 }, // Stout Halfling
  "10": { STR: 2, DEX: 0, CON: 0, INT: 0, WIS: 0, CHA: 1 }, // Dragonborn
  "11": { STR: 0, DEX: 0, CON: 0, INT: 2, WIS: 0, CHA: 0 }, // Gnome
  "12": { STR: 0, DEX: 1, CON: 0, INT: 2, WIS: 0, CHA: 0 }, // Forest Gnome
  "13": { STR: 0, DEX: 0, CON: 1, INT: 2, WIS: 0, CHA: 0 }, // Rock Gnome
  "14": { STR: 0, DEX: 0, CON: 0, INT: 0, WIS: 0, CHA: 2 }, // Half-Elf
  "15": { STR: 2, DEX: 0, CON: 1, INT: 0, WIS: 0, CHA: 0 }, // Half-Orc
  "16": { STR: 0, DEX: 0, CON: 0, INT: 1, WIS: 0, CHA: 2 }, // Tiefling
}

const raceNames: { [key: string]: string } = {
  "1": "Human",
  "2": "Dwarf",
  "3": "Hill Dwarf",
  "4": "Elf",
  "5": "High Elf",
  "6": "Wood Elf",
  "7": "Halfling",
  "8": "Lightfoot Halfling",
  "9": "Stout Halfling",
  "10": "Dragonborn",
  "11": "Gnome",
  "12": "Forest Gnome",
  "13": "Rock Gnome",
  "14": "Half-Elf",
  "15": "Half-Orc",
  "16": "Tiefling",
}

function useControllableState<T>({
  value,
  onChange,
  defaultValue,
}: {
  value?: T
  onChange?: (next: T) => void
  defaultValue: T
}): [T, (next: T) => void] {
  const isControlled = typeof onChange === "function"
  const [internalValue, setInternalValue] = React.useState<T>(() =>
    value !== undefined ? value : defaultValue
  )

  React.useEffect(() => {
    if (!isControlled && value !== undefined) {
      setInternalValue(value)
    }
  }, [value, isControlled])

  const setValue = React.useCallback(
    (next: T) => {
      if (isControlled) {
        onChange?.(next)
      } else {
        setInternalValue(next)
      }
    },
    [isControlled, onChange]
  )

  const resolvedValue = isControlled
    ? value !== undefined
      ? value
      : defaultValue
    : internalValue

  return [resolvedValue, setValue]
}

export function DiceRoller({
  raceId,
  setRaceId,
  showRaceSelect = true,
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
  onRollComplete,
}: DiceRollerProps) {
  const [currentRaceId, updateRaceId] = useControllableState({
    value: raceId,
    onChange: setRaceId,
    defaultValue: "",
  })
  const [currentStrength, updateStrength] = useControllableState({
    value: strength,
    onChange: setStrength,
    defaultValue: "10",
  })
  const [currentDexterity, updateDexterity] = useControllableState({
    value: dexterity,
    onChange: setDexterity,
    defaultValue: "10",
  })
  const [currentConstitution, updateConstitution] = useControllableState({
    value: constitution,
    onChange: setConstitution,
    defaultValue: "10",
  })
  const [currentIntelligence, updateIntelligence] = useControllableState({
    value: intelligence,
    onChange: setIntelligence,
    defaultValue: "10",
  })
  const [currentWisdom, updateWisdom] = useControllableState({
    value: wisdom,
    onChange: setWisdom,
    defaultValue: "10",
  })
  const [currentCharisma, updateCharisma] = useControllableState({
    value: charisma,
    onChange: setCharisma,
    defaultValue: "10",
  })
  const [rollingAttribute, setRollingAttribute] = useState<Attribute | null>(null)
  const [diceResults, setDiceResults] = useState<Record<Attribute, number[]>>({
    STR: [], DEX: [], CON: [], INT: [], WIS: [], CHA: []
  })
  const [halfElfExtra, setHalfElfExtra] = useState<Attribute[]>([])

  const attributes: { id: Attribute; name: string }[] = [
    { id: "STR", name: "Strength" },
    { id: "DEX", name: "Dexterity" },
    { id: "CON", name: "Constitution" },
    { id: "INT", name: "Intelligence" },
    { id: "WIS", name: "Wisdom" },
    { id: "CHA", name: "Charisma" },
  ]

  const secureRandomInt = (min: number, max: number): number => {
    const range = max - min + 1
    const array = new Uint32Array(1)
    window.crypto.getRandomValues(array)
    return (array[0] % range) + min
  }

  const rollDiceForAttribute = async (attribute: Attribute) => {
    setRollingAttribute(attribute)
    setDiceResults(prev => ({ ...prev, [attribute]: [] }))

    // Simulate rolling 5 dice
    const results: number[] = []
    for (let i = 0; i < 5; i++) {
      await new Promise(resolve => setTimeout(resolve, 200))
      const roll = secureRandomInt(1, 6)
      results.push(roll)
      setDiceResults(prev => ({ ...prev, [attribute]: [...results] }))
    }

    // Calculate final result (remove min and max values, take sum of middle three)
    const sorted = [...results].sort((a, b) => a - b)
    sorted.shift() // Remove min value
    sorted.pop() // Remove max value
    const baseSum = sorted.reduce((a, b) => a + b, 0)

    // Calculate racial bonus
    const raceBonus = racialBonus[currentRaceId as RaceId]
    const baseRaceBonus = raceBonus ? raceBonus[attribute] || 0 : 0
    let extraBonus = 0

    // Half-elf extra bonus handling
    if (currentRaceId === "14" && halfElfExtra.includes(attribute)) {
      extraBonus = 1
    }

    const total = baseSum + baseRaceBonus + extraBonus

    // Automatically set corresponding attribute value
    const setterMap: Record<Attribute, (value: string) => void> = {
      STR: updateStrength,
      DEX: updateDexterity,
      CON: updateConstitution,
      INT: updateIntelligence,
      WIS: updateWisdom,
      CHA: updateCharisma,
    }
    setterMap[attribute](total.toString())

    onRollComplete?.({
      diceResults: [...results],
      baseSum,
      bonus: baseRaceBonus + extraBonus,
      total,
      race: raceNames[currentRaceId] ?? "Unknown Race",
      attribute,
    })

    setRollingAttribute(null)
  }

  const handleHalfElfExtraChange = (attribute: Attribute, checked: boolean) => {
    if (checked) {
      if (halfElfExtra.length < 2) {
        setHalfElfExtra([...halfElfExtra, attribute])
      }
    } else {
      setHalfElfExtra(halfElfExtra.filter(a => a !== attribute))
    }
  }

  const getRaceBonus = (attribute: Attribute): number => {
    const raceBonus = racialBonus[currentRaceId as RaceId]
    const baseBonus = raceBonus ? raceBonus[attribute] || 0 : 0
    let extraBonus = 0

    if (currentRaceId === "14" && halfElfExtra.includes(attribute)) {
      extraBonus = 1
    }

    return baseBonus + extraBonus
  }

  const getCurrentResults = (attribute: Attribute) => {
    return diceResults[attribute]
  }

  const getFinalValue = (attribute: Attribute): number => {
    const results = diceResults[attribute]
    if (results.length === 0) return 0

    const sorted = [...results].sort((a, b) => a - b)
    sorted.shift() // Remove min value
    sorted.pop() // Remove max value
    const baseSum = sorted.reduce((a, b) => a + b, 0)

    return baseSum + getRaceBonus(attribute)
  }

  // 一键投掷所有6个属性
  const rollAllAttributes = async () => {
    if (!currentRaceId) return
    
    for (const attr of attributes) {
      await rollDiceForAttribute(attr.id)
      // 添加短暂延迟，让用户能看到每个属性的投掷过程
      await new Promise(resolve => setTimeout(resolve, 500))
    }
  }

  // 恢复所有属性为10
  const resetAllAttributes = () => {
    updateStrength("10")
    updateDexterity("10")
    updateConstitution("10")
    updateIntelligence("10")
    updateWisdom("10")
    updateCharisma("10")
    setDiceResults({
      STR: [], DEX: [], CON: [], INT: [], WIS: [], CHA: []
    })
  }

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 dark:bg-slate-900/60 border border-blue-200 dark:border-slate-700 rounded-lg p-4">
        <p className="text-sm text-blue-800 dark:text-blue-100">
          <strong>Tip:</strong> You can roll dice for any of the 6 attributes! Each attribute has its own roll button.
        </p>
      </div>

      {/* 快速操作按钮 */}
      <div className="flex flex-wrap gap-3 justify-center">
        <Button
          onClick={rollAllAttributes}
          disabled={!currentRaceId || rollingAttribute !== null}
          variant="default"
          size="sm"
          className="bg-green-600 hover:bg-green-700 text-white"
        >
          One-click throw
        </Button>
        <Button
          onClick={resetAllAttributes}
          variant="outline"
          size="sm"
          className="border-gray-300 hover:bg-gray-50 dark:border-slate-600 dark:hover:bg-slate-800"
        >
          reset
        </Button>
      </div>

      {showRaceSelect && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="race">Race</Label>
            <Select value={currentRaceId} onValueChange={updateRaceId}>
              <SelectTrigger id="race">
                <SelectValue placeholder="Select a race" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(raceNames).map(([id, raceName]) => (
                  <SelectItem key={id} value={id}>
                    {raceName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Half-elf extra bonus selection */}
      {currentRaceId === "14" && (
        <div className="p-4 border border-blue-200 dark:border-slate-700 rounded-lg bg-blue-50 dark:bg-slate-900/60">
          <Label className="text-sm font-medium mb-2 block">
            Half-elf Extra Bonuses (Select 2 attributes, each +1)
          </Label>
          <div className="flex flex-wrap gap-4">
            {attributes
              .filter(attr => attr.id !== "CHA") // Charisma already has +2, cannot select
              .map(attr => (
                <div key={attr.id} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id={`halfelf-${attr.id}`}
                    checked={halfElfExtra.includes(attr.id)}
                    onChange={(e) =>
                      handleHalfElfExtraChange(attr.id as Attribute, e.target.checked)
                    }
                    disabled={halfElfExtra.length >= 2 && !halfElfExtra.includes(attr.id)}
                    className="h-4 w-4 text-blue-600"
                  />
                  <Label htmlFor={`halfelf-${attr.id}`} className="text-sm">
                    {attr.name} ({attr.id})
                  </Label>
                </div>
              ))}
          </div>
          {halfElfExtra.length === 2 && (
            <p className="text-xs text-green-600 dark:text-green-400 mt-2">
              Selected 2 attributes: {halfElfExtra.map(a => attributes.find(attr => attr.id === a)?.name).join(", ")}
            </p>
          )}
        </div>
      )}

      {/* Attribute cards with individual roll buttons */}
      <div className="grid grid-cols-6 gap-4">
        {attributes.map(attr => {
          const results = getCurrentResults(attr.id)
          const finalValue = getFinalValue(attr.id)
          const isRolling = rollingAttribute === attr.id
          const currentValue = {
            STR: currentStrength,
            DEX: currentDexterity,
            CON: currentConstitution,
            INT: currentIntelligence,
            WIS: currentWisdom,
            CHA: currentCharisma,
          }[attr.id]

          return (
            <div key={attr.id} className="p-3 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900/60 shadow-sm dark:shadow-none">
              <div className="text-center mb-2">
                <div className="text-sm font-bold text-gray-800 dark:text-gray-100">{attr.name}</div>
                <div className="text-xs text-gray-600 dark:text-slate-300">({attr.id})</div>
              </div>

              <div className="text-center mb-2">
                <div className="text-xl font-bold text-blue-600 dark:text-blue-300">
                  {currentValue || "-"}
                </div>
                <div className="text-xs text-gray-500 dark:text-slate-400">
                  +{getRaceBonus(attr.id)}
                </div>
              </div>

              <Button
                onClick={() => rollDiceForAttribute(attr.id)}
                disabled={isRolling || !currentRaceId}
                className="w-full mb-2"
                size="sm"
              >
                {isRolling ? "Rolling..." : "Roll"}
              </Button>

              {results.length > 0 && (
                <div className="text-center space-y-2">
                  <div className="flex justify-center space-x-1">
                    {results.map((result, index) => (
                      <div
                        key={index}
                        className="w-8 h-8 border border-gray-300 dark:border-slate-600 rounded flex items-center justify-center text-sm font-bold bg-white dark:bg-slate-800"
                      >
                        {result}
                      </div>
                    ))}
                  </div>

                  <div className="text-xs text-gray-600 dark:text-slate-400">
                    <p>
                      Dice: {results.join(", ")} →
                      Remove min({Math.min(...results)}) and max({Math.max(...results)}) =
                      {[...results].sort((a, b) => a - b).slice(1, 4).reduce((a, b) => a + b, 0)}
                    </p>
                    <p>
                      +{getRaceBonus(attr.id)} racial bonus =
                      <strong className="text-green-600 dark:text-green-400 ml-1">{finalValue}</strong>
                    </p>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
