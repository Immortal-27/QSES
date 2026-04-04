import { CompressedTexture } from 'three/src/textures/CompressedTexture.js';
import { CompressedPixelFormat, TextureDataType } from 'three/src/constants.js';

export class CompressedCubeTexture extends CompressedTexture {
    readonly isCompressedCubeTexture: true;
    readonly isCubeTexture: true;

    constructor(
        images: Array<{ width: number; height: number }>,
        format?: CompressedPixelFormat,
        type?: TextureDataType,
    );
}
