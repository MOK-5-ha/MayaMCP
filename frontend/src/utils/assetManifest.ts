export interface ImageAsset {
  key: string;
  path: string;
}

export interface AudioAsset {
  key: string;
  path: string;
  type: 'music' | 'sfx';
  title?: string;
  placeholder?: boolean;
}

export interface AssetManifest {
  version: string;
  spritesheets?: Array<{
    key: string;
    path: string;
    frameWidth: number;
    frameHeight: number;
  }>;
  images?: ImageAsset[];
  audio?: AudioAsset[];
  soundtrack?: {
    startTrack?: string;
    playlist?: string[];
  };
}

export const MANIFEST_REGISTRY_KEY = 'maya_asset_manifest';
