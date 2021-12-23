#include <cupy/complex.cuh>

#define CUDART_PI_F 3.141592654f

__constant__ float zElemConst[256];
__constant__ float xElemConst[256];
__constant__ float tangElemConst[256];


__device__ float xRefract(float const zElem, float const xElem,
                          float const zPix, float const xPix,
                          float const sosInterface, float const sosSample,
                          float const timePrec) {
    float xRefractLo, sinRatioLo, xRefractHi, sinRatioHi, timeOld;
    float xRefractNew, distInterf, distSample, sinRatioNew, timeNew;

    float const cRatio = sosInterface / sosSample;
    // Initial refraction points
    xRefractLo = xElem;
    sinRatioLo = 0.f;

    xRefractHi = xElem - zElem * (xPix - xElem) / (zPix - zElem);
    sinRatioHi = 1.f;

    timeOld = hypotf(xRefractHi - xElem, zElem) / sosInterface
            + hypotf(xPix - xRefractHi, zPix ) / sosSample;

    // Iterations
    do {
        xRefractNew = xRefractLo + (xRefractHi-xRefractLo)*(cRatio-sinRatioLo)/(sinRatioHi-sinRatioLo);
        distInterf  = hypotf(xRefractNew - xElem, zElem);
        distSample  = hypotf(xPix - xRefractNew, zPix);
        sinRatioNew = ((xRefractNew - xElem) / distInterf)
                / ((xPix - xRefractNew) / distSample);
        timeNew     = distInterf / sosInterface + distSample / sosSample;
        if (fabs(timeNew-timeOld) < timePrec) {
            break;
        }
        if (sinRatioNew < cRatio) {
            xRefractLo = xRefractNew;
            sinRatioLo = sinRatioNew;
        }
        else {
            xRefractHi = xRefractNew;
            sinRatioHi = sinRatioNew;
        }
        timeOld = timeNew;
    } while(true);
    return xRefractNew;
}


extern "C"
__global__ void
iqRaw2Lri(complex<float> *iqLri, const complex<float> *iqRaw,
          const int nElem,
          const int nSeq, const int nTx, const int nSamp,
          const float *zPix, const int nZPix,
          const float *xPix, const int nXPix,
          float const sos, float const fs, float const fn,
          const float *txApCentZ, const float *txApCentX,
          const int *rxApOrigElem, const int nRx,
          const float minRxTang, const float maxRxTang,
          float const initDel,
          // wedge parameters,
          const float sosInterface, // wedge speed of sound
          const float timePrec
          ) {

    int z = blockIdx.x * blockDim.x + threadIdx.x;
    int x = blockIdx.y * blockDim.y + threadIdx.y;
    int iGlobalTx = blockIdx.z * blockDim.z + threadIdx.z;

    if(z >= nZPix || x >= nXPix || iGlobalTx >= nSeq*nTx) {
        return;
    }
    int iTx = iGlobalTx % nTx;

    int iElem, offset;
    float interpWgh;
    float txTime, rxTime, xRefr, rxTang, txApod, rxApod, time, iSamp;
    float modSin, modCos, pixWgh;
    const float omega = 2 * CUDART_PI_F * fn;
    const float sosInv = 1 / sos;
    const float sosInvInterface = 1 / sosInterface;
    const float nSigma = 3; // number of sigmas in half of the apodization Gaussian curve
    const float twoSigSqrInv = nSigma * nSigma * 0.5f;
    const float rngRxTangInv = 2 / (maxRxTang - minRxTang); // inverted half range
    const float centRxTang = (maxRxTang + minRxTang) * 0.5f;
    complex<float> pix(0.0f, 0.0f), samp(0.0f, 0.0f), modFactor;

    int txOffset = iGlobalTx * nSamp * nRx;

    xRefr = xRefract(txApCentZ[iTx], txApCentX[iTx], zPix[z], xPix[x], sosInterface, sos, timePrec);

    txTime = hypotf(0.f - txApCentZ[iTx], xRefr - txApCentX[iTx]) * sosInvInterface
            + hypotf(zPix[z] - 0.f, xPix[x] - xRefr) * sosInv;

    txApod = 1.0f;

    pixWgh = 0.0f;
    pix.real(0.0f);
    pix.imag(0.0f);

    if(txApod != 0.0f) {
        for(int iRx = 0; iRx < nRx; ++iRx) {
            iElem = iRx + rxApOrigElem[iTx];
            if(iElem < 0 || iElem >= nElem) continue;

            xRefr = xRefract(zElemConst[iElem], xElemConst[iElem], zPix[z], xPix[x], sosInterface, sos, timePrec);

            rxTime	= hypotf(xRefr - xElemConst[iElem], 0.f - zElemConst[iElem]) * sosInvInterface
                    + hypotf(xPix[x] - xRefr, zPix[z] - 0.f) * sosInv;


            rxTang = __fdividef(xRefr - xElemConst[iElem], 0.f - zElemConst[iElem]);
            rxTang = __fdividef(rxTang-tangElemConst[iElem], 1.f+rxTang*tangElemConst[iElem]);

            if(rxTang < minRxTang || rxTang > maxRxTang) continue;

            rxApod = (rxTang - centRxTang) * rngRxTangInv;
            rxApod = __expf(-rxApod * rxApod * twoSigSqrInv);

            time = txTime + rxTime + initDel;

            iSamp = time * fs;
            if(iSamp < 0.0f || iSamp >= static_cast<float>(nSamp - 1)) {
                continue;
            }
            offset = txOffset + iRx * nSamp;
            interpWgh = modff(iSamp, &iSamp);
            int intSamp = int(iSamp);

            __sincosf(omega * time, &modSin, &modCos);
            complex<float> modFactor = complex<float>(modCos, modSin);

            samp = iqRaw[offset + intSamp] * (1 - interpWgh) + iqRaw[offset + intSamp + 1] * interpWgh;
            pix += samp * modFactor * rxApod;
            pixWgh += rxApod;
        }
    }
    if(pixWgh == 0.0f) {
        iqLri[z + x*nZPix + iGlobalTx*nZPix*nXPix] = complex<float>(0.0f, 0.0f);
    } else {
        iqLri[z + x*nZPix + iGlobalTx*nZPix*nXPix] = pix / pixWgh * txApod;
    }
}