import type { PhotoGroupName } from '@/types/report'

export interface PhotoGroupConfig {
  name: PhotoGroupName
  label: string
  section: string
  min: number
  max: number
}

export const PHOTO_GROUPS: readonly PhotoGroupConfig[] = [
  {
    name: 'building_details_building_photo',
    label: 'Building Photo',
    section: 'Building Details',
    min: 1,
    max: 1,
  },
  {
    name: 'superstructure_rebar_scanning_photos',
    label: 'Rebar Scanning Photos',
    section: 'Superstructure - Rebar Scanning',
    min: 1,
    max: 5,
  },
  {
    name: 'superstructure_rebound_hammer_test_photos',
    label: 'Rebound Hammer Test Photos',
    section: 'Superstructure - Rebound Hammer Test',
    min: 1,
    max: 5,
  },
  {
    name: 'superstructure_concrete_coring_photos',
    label: 'Concrete Coring Photos',
    section: 'Superstructure - Concrete Core Extraction',
    min: 1,
    max: 5,
  },
  {
    name: 'superstructure_core_samples_family_pic',
    label: 'Core Samples Family Photo',
    section: 'Superstructure - Concrete Core Extraction',
    min: 1,
    max: 2,
  },
  {
    name: 'superstructure_rebar_extraction_photos',
    label: 'Rebar Extraction Photos',
    section: 'Superstructure - Rebar Extraction',
    min: 1,
    max: 5,
  },
  {
    name: 'superstructure_rebar_samples_family_pic',
    label: 'Rebar Samples Family Photo',
    section: 'Superstructure - Rebar Extraction',
    min: 1,
    max: 2,
  },
  {
    name: 'superstructure_chipping_of_slab_photos',
    label: 'Chipping of Slab Photos',
    section: 'Superstructure - Chipping of Existing Slab',
    min: 1,
    max: 2,
  },
  {
    name: 'superstructure_restoration_photos',
    label: 'Restoration Photos',
    section: 'Superstructure - Restoration Works',
    min: 1,
    max: 5,
  },
  {
    name: 'substructure_coring_for_foundation_photos',
    label: 'Foundation Coring Photos',
    section: 'Substructure - Concrete Core Extraction',
    min: 1,
    max: 3,
  },
  {
    name: 'substructure_rebar_scanning_for_foundation_photos',
    label: 'Foundation Rebar Scanning Photos',
    section: 'Substructure - Rebar Scanning',
    min: 1,
    max: 3,
  },
  {
    name: 'substructure_restoration_backfilling_compaction_photos',
    label: 'Restoration, Backfilling, and Compaction Photos',
    section: 'Substructure - Restoration for Coring Works',
    min: 1,
    max: 5,
  },
]
