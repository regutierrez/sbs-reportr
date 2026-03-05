import type { AnnexGroupName } from '@/types/report'

export interface AnnexGroupConfig {
  name: AnnexGroupName
  label: string
  section: string
  numeral: string
}

export const ANNEX_GROUPS: readonly AnnexGroupConfig[] = [
  {
    name: 'rebar_scanning_output',
    label: 'Rebar Scanning Output',
    section: 'ANNEX I',
    numeral: 'I',
  },
  {
    name: 'rebound_number_test_results',
    label: 'Rebound Number Test Results',
    section: 'ANNEX II',
    numeral: 'II',
  },
  {
    name: 'compressive_strength_test_results_superstructure',
    label: 'Compressive Strength Test Results (Superstructure)',
    section: 'ANNEX III',
    numeral: 'III',
  },
  {
    name: 'tensile_strength_test_results',
    label: 'Tensile Strength Test Results',
    section: 'ANNEX IV',
    numeral: 'IV',
  },
  {
    name: 'compressive_strength_test_results_substructure',
    label: 'Compressive Strength Test Results (Substructure)',
    section: 'ANNEX V',
    numeral: 'V',
  },
  {
    name: 'rebar_scanning_results_for_foundation',
    label: 'Rebar Scanning Results for Foundation',
    section: 'ANNEX VI',
    numeral: 'VI',
  },
  {
    name: 'material_tests_mapping',
    label: 'Material Tests Mapping',
    section: 'ANNEX VII',
    numeral: 'VII',
  },
]
