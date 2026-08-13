#include "OptiLabCore.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace {
constexpr double pi = 3.14159265358979323846264338327950288;
constexpr double tiny = 0.000001;
}

double OptiLabCore::OnePole::lp(double x, double a) { z += a * (x - z); return z; }
double OptiLabCore::OnePole::lp2(double x, double a) { z1 += a*(x-z1); z2 += a*(z1-z2); return z2; }
double OptiLabCore::OnePole::hp(double x, double a) { z += a*(x-z); return x-z; }
void OptiLabCore::OnePole::reset() { z=z1=z2=0.0; }
double OptiLabCore::Allpass1::run(double x,double c){ const double y=-c*x+x1+c*y1; x1=x;y1=y;return y; }
void OptiLabCore::Allpass1::reset(){x1=y1=0.0;}
double OptiLabCore::PeakEnv::run(double det,double attack,double release){e=det>e?det+attack*(e-det):det+release*(e-det);return e;}
double OptiLabCore::PeakEnv::set(double value){e=value;return e;}

double OptiLabCore::GainCell::bandLimitPd(double det,double thresh,double attack,double relBase,double relSlow,double pdAmt){
    if(gain<=0.0)gain=1.0;
    double depth=OptiLabCore::clamp((env-thresh)/std::max(thresh*2.5,tiny),0.0,1.0);
    double relNow=relBase*(1.0-pdAmt*depth)+relSlow*(pdAmt*depth); env=det>env?det+attack*(env-det):det+relNow*(env-det); env=std::max(env,tiny);
    double targetGain=env>thresh?thresh/env:1.0; targetGain=OptiLabCore::clamp(targetGain,0.10,1.0);
    depth=OptiLabCore::clamp((1.0-gain)/0.75,0.0,1.0); relNow=relBase*(1.0-pdAmt*depth)+relSlow*(pdAmt*depth);
    gain=targetGain<gain?targetGain+attack*(gain-targetGain):targetGain+relNow*(gain-targetGain); return gain;
}
double OptiLabCore::GainCell::bandLimitPdSoft(double det,double thresh,double attack,double relBase,double relSlow,double pdAmt,double ratio,double knee,double minGain){
    if(gain<=0.0)gain=1.0;
    double depth=OptiLabCore::clamp((env-thresh)/std::max(thresh*2.5,tiny),0.0,1.0);
    double relNow=relBase*(1.0-pdAmt*depth)+relSlow*(pdAmt*depth); env=det>env?det+attack*(env-det):det+relNow*(env-det); env=std::max(env,tiny);
    const double over=env/std::max(thresh,tiny); double targetGain=1.0; if(over>1.0){const double soft=OptiLabCore::clamp((over-1.0)/std::max((over-1.0)+knee,tiny),0.0,1.0); const double compressed=std::pow(over,(1.0/std::max(ratio,1.01))-1.0); targetGain=1.0-soft*(1.0-compressed);} targetGain=OptiLabCore::clamp(targetGain,minGain,1.0);
    depth=OptiLabCore::clamp((1.0-gain)/0.75,0.0,1.0); relNow=relBase*(1.0-pdAmt*depth)+relSlow*(pdAmt*depth); gain=targetGain<gain?targetGain+attack*(gain-targetGain):targetGain+relNow*(gain-targetGain); return gain;
}
double OptiLabCore::GainCell::linkedLimiter(double det,double thresh,double attack,double release){if(gain<=0.0)gain=1.0;double targetGain=det>thresh?thresh/std::max(det,tiny):1.0;targetGain=OptiLabCore::clamp(targetGain,0.08,1.0);gain=targetGain<gain?targetGain+attack*(gain-targetGain):targetGain+release*(gain-targetGain);return gain;}
double OptiLabCore::EventCell::run(double det,double threshDb,double quietThreshold,double attack,double rate,double minimumRelease,double maximumRelease){
    if(gain<=0.0)gain=1.0;
    if(env==0.0&&det<quietThreshold){gain=1.0;return gain;}
    double instantDb=OptiLabCore::linToDb(std::max(det,0.000000000001))-threshDb;instantDb=std::max(instantDb,0.0);
    if(env==0.0&&instantDb==0.0){gain=1.0;return gain;}
    if(instantDb>env)env=instantDb+attack*(env-instantDb);else{const double releaseSeconds=OptiLabCore::clamp(env/300.0,0.004,0.060);const double release=env<1.2?minimumRelease:env>18.0?maximumRelease:std::exp(-1.0/std::max(1.0,rate*releaseSeconds));env=instantDb+release*(env-instantDb);}
    if(env<0.00001)env=0.0;
    if(env>18.5){gain=0.12;return gain;}
    gain=OptiLabCore::clamp(OptiLabCore::dbToLin(-env),0.12,1.0);return gain;
}
double OptiLabCore::SmoothRounder::run(double x,double amt){amt=OptiLabCore::clamp(amt,0.0,1.0);if(amt<=0.0000001)return x;const double sat=std::sin(OptiLabCore::clamp(x,-pi*0.5,pi*0.5));const double apply=OptiLabCore::clamp(std::abs(prevSat+sat)*0.5*amt,0.0,1.0);const double y=x*(1.0-apply)+sat*apply;prevSat=sat;return y;}
void OptiLabCore::SmoothRounder::reset(){prevSat=0.0;}
double OptiLabCore::DcClipper::run(double x,double th,double amt,double kneeMul,double cancelAmt,double a){const double clipped=OptiLabCore::softClipKnee(x,th,kneeMul);double y=clipped;if(cancelAmt>0.0){const double dist=clipped-x;dcZ+=a*(dist-dcZ);y-=dcZ*cancelAmt;}return x*(1.0-amt)+y*amt;}
void OptiLabCore::DcClipper::reset(){dcZ=0.0;}
double OptiLabCore::BassClipper::run(double x,double th,double amt,double kneeMul,double drive,double resMix,double a){drive=std::max(drive,1.0);const double driven=x*drive;const double clipped=OptiLabCore::softClipKnee(driven,th,kneeMul)/drive;const double dist=clipped-x;z1+=a*(dist-z1);z2+=a*(z1-z2);const double clipMix=amt*(0.50+0.50*amt);const double residueMix=amt*resMix*(0.35+0.65*amt);return x+dist*clipMix+z2*residueMix;}
void OptiLabCore::BassClipper::reset(){z1=z2=0.0;}
void OptiLabCore::Biquad::setLowpass(double freq,double q,double sampleRate){freq=OptiLabCore::clamp(freq,20.0,sampleRate*0.45);const double w0=2.0*pi*freq/sampleRate,cw=std::cos(w0),sw=std::sin(w0),alpha=sw/(2.0*q),norm=1.0/(1.0+alpha);a0=((1.0-cw)*0.5)*norm;a1=(1.0-cw)*norm;a2=a0;b1=(-2.0*cw)*norm;b2=(1.0-alpha)*norm;}
void OptiLabCore::Biquad::setPeak(double freq,double q,double gainDb,double sampleRate){freq=OptiLabCore::clamp(freq,20.0,sampleRate*0.45);const double A=std::exp(gainDb*0.057564627324851),w0=2.0*pi*freq/sampleRate,cw=std::cos(w0),sw=std::sin(w0),alpha=sw/(2.0*q),b0=1.0+alpha*A,bb1=-2.0*cw,bb2=1.0-alpha*A,aa0=1.0+alpha/A,aa1=-2.0*cw,aa2=1.0-alpha/A,norm=1.0/aa0;a0=b0*norm;a1=bb1*norm;a2=bb2*norm;b1=aa1*norm;b2=aa2*norm;}
void OptiLabCore::Biquad::setLowShelf(double freq, double slope, double gainDb, double sampleRate) {
    freq = OptiLabCore::clamp(freq, 20.0, sampleRate * 0.45);
    const double A = std::exp(gainDb * 0.057564627324851);
    const double w0 = 2.0 * pi * freq / sampleRate;
    const double cw = std::cos(w0);
    const double sw = std::sin(w0);
    const double alpha = sw * 0.5 * std::sqrt((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0);
    const double sqrtA = std::sqrt(A);
    const double b0 = A * ((A + 1.0) - (A - 1.0) * cw + 2.0 * sqrtA * alpha);
    const double bb1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cw);
    const double bb2 = A * ((A + 1.0) - (A - 1.0) * cw - 2.0 * sqrtA * alpha);
    const double aa0 = (A + 1.0) + (A - 1.0) * cw + 2.0 * sqrtA * alpha;
    const double aa1 = -2.0 * ((A - 1.0) + (A + 1.0) * cw);
    const double aa2 = (A + 1.0) + (A - 1.0) * cw - 2.0 * sqrtA * alpha;
    const double norm = 1.0 / aa0;
    a0 = b0 * norm;
    a1 = bb1 * norm;
    a2 = bb2 * norm;
    b1 = aa1 * norm;
    b2 = aa2 * norm;
}

void OptiLabCore::Biquad::copyCoefficientsFrom(const Biquad& source) {
    a0 = source.a0;
    a1 = source.a1;
    a2 = source.a2;
    b1 = source.b1;
    b2 = source.b2;
}

double OptiLabCore::Biquad::run(double x){const double y=a0*x+a1*x1+a2*x2-b1*y1-b2*y2;x2=x1;x1=x;y2=y1;y1=y;return y;}
void OptiLabCore::Biquad::reset(){x1=x2=y1=y2=0.0;}
void OptiLabCore::FoundationGuard::reset() {
    Biquad* filters[] = {
        &lp70L, &lp70R, &lp250L, &lp250R, &lp420L, &lp420R,
        &lp3700L, &lp3700R, &shelfL, &shelfR, &bodyL, &bodyR
    };
    for (Biquad* filter : filters) {
        filter->reset();
    }
    deepFast.e = usefulFast.e = midFast.e = 0.0;
    deepSlow.e = usefulSlow.e = midSlow.e = 0.0;
    primed = false;
    ageSamples = 0;
    controlCounter = 15;
    coefficientCounter = 63;
    fastDeepBoostEvidenceDb = fastUsefulBoostEvidenceDb = 0.0;
    fastDeepCutEvidenceDb = fastUsefulCutEvidenceDb = 0.0;
    deepBoostStateDb = usefulBoostStateDb = 0.0;
    deepCutStateDb = usefulCutStateDb = 0.0;
    deepTargetDb = usefulTargetDb = 0.0;
    deepTargetGain = usefulTargetGain = 1.0;
    voiceTarget = voiceGain = 1.0;
    feedbackB1Accum = feedbackB2Accum = 0.0;
    feedbackCount = 0;
    feedbackRatioDb = -120.0;
    feedbackServoDb = 0.0;
    feedbackBurden = 0.0;
    rumbleSubAccum = rumbleTotalAccum = 0.0;
    rumbleCount = 0;
    rumbleRatioDb = -120.0;
    rumbleSubEnv = rumbleTotalEnv = 0.0;
    rumbleState = 0.0;
}

double OptiLabCore::dbToLin(double db){return std::exp(db*0.11512925464970229);} double OptiLabCore::linToDb(double x){return std::log(std::max(x,0.0000001))*8.6858896380650366;} double OptiLabCore::clamp(double x,double lo,double hi){return std::min(std::max(x,lo),hi);} double OptiLabCore::smoothstep01(double x) {
    x = clamp(x, 0.0, 1.0);
    return x * x * (3.0 - 2.0 * x);
}

double OptiLabCore::adaptiveBassBoostCurve(double x) {
    x = clamp(x, 0.0, 1.0);
    double t = 0.0;
    if (x <= 0.25) {
        t = x;
        return -0.4571428571*t*t*t + 0.9142857143*t*t + t;
    }
    if (x <= 0.50) {
        t = x - 0.25;
        return -0.5468624845*t*t*t + 1.0510013351*t*t + 1.3714285714*t + 0.3;
    }
    if (x <= 0.65) {
        t = x - 0.50;
        return -60.4153393502*t*t*t + 10.4330174081*t*t + 1.7943925234*t + 0.7;
    }
    t = x - 0.65;
    return -0.9672424138*t*t*t - 0.7011439362*t*t + 0.8462623413*t + 1.0;
}

double OptiLabCore::adaptiveBassCutCurve(double x) {
    x = clamp(x, 0.0, 1.0);
    double t = 0.0;
    if (x <= 0.25) {
        t = x;
        return -0.4571428571*t*t*t + 0.9142857143*t*t + t;
    }
    if (x <= 0.50) {
        t = x - 0.25;
        return -0.5468624845*t*t*t + 1.0510013351*t*t + 1.3714285714*t + 0.3;
    }
    if (x <= 0.65) {
        t = x - 0.50;
        return clamp(-98.0269989616*t*t*t + 16.0747663551*t*t + 1.7943925234*t + 0.7, 0.0, 1.0);
    }
    return 1.0;
}

double OptiLabCore::absmax2(double a,double b){return std::max(std::abs(a),std::abs(b));}
double OptiLabCore::softClipKnee(double x,double th,double kneeMul){const double ax=std::abs(x);if(ax<=th)return x;const double sign=x<0.0?-1.0:1.0,over=ax-th,knee=std::max(tiny,th*kneeMul),y=th+knee*(1.0-std::exp(-over/knee));return sign*y;}
double OptiLabCore::limiterBandClip(double x,double limit,double amount,double soft){double clipped=x;if(soft<=0.0){if(std::abs(x)>limit)clipped=std::copysign(limit,x);}else{const double magnitude=std::abs(x),sign=x<0.0?-1.0:1.0,knee=limit*(1.0-0.70*soft),span=std::max(0.000000001,limit-knee);if(magnitude>knee)clipped=sign*(knee+span*(1.0-std::exp(-(magnitude-knee)/span)));}return x*(1.0-amount)+clipped*amount;}
double OptiLabCore::purePeakRound(double x,double th,double amt,double driveMul){if(amt<=0.0)return x;th=std::max(th,tiny);const double d=driveMul/th,lim=pi*0.5,y=std::sin(clamp(x*d,-lim,lim))/d;return x*(1.0-amt)+y*amt;}
double OptiLabCore::hardLimit(double x,double ceilingValue){return std::min(std::max(x,-ceilingValue),ceilingValue);} double OptiLabCore::hybridShaveToLimit(double x, double limit, double depthDb) {
    const double ax = std::abs(x);
    const double kneeStart = limit * dbToLin(-std::max(depthDb, 0.001));
    const double span = std::max(limit - kneeStart, 1.0e-12);
    if (ax <= kneeStart) return x;
    const double sign = x < 0.0 ? -1.0 : 1.0;
    const double over = ax - kneeStart;
    const double y = kneeStart + span * (1.0 - std::exp(-over / span));
    return sign * std::min(y, limit);
}

double OptiLabCore::hybridEventTonalCorrelation(std::int64_t nowAbs) const {
    constexpr int taps = 8;
    constexpr double searchFraction = 0.04;
    double best = -1.0;
    const std::int64_t onsets[3]{hybridOnset1, hybridOnset2, hybridOnset3};
    for (const std::int64_t onset : onsets) {
        if (onset <= -100000000LL) continue;
        const std::int64_t base = nowAbs - onset;
        if (base < hybridPeriodMinSamples || base > hybridPeriodMaxSamples) continue;
        for (int searchIndex = -3; searchIndex <= 3; ++searchIndex) {
            const auto lag = static_cast<int>(std::floor(
                static_cast<double>(base) *
                (1.0 + searchFraction * static_cast<double>(searchIndex) / 3.0) + 0.5));
            if (lag < hybridPeriodMinSamples || lag > hybridPeriodMaxSamples) continue;
            double dot = 0.0;
            double energyA = 0.0;
            double energyB = 0.0;
            int count = 0;
            for (int tap = 0; tap < taps; ++tap) {
                const int offset = static_cast<int>(std::floor(
                    static_cast<double>(tap) * static_cast<double>(std::max(1, lag - 1)) /
                    static_cast<double>(taps - 1) + 0.5));
                const std::int64_t aAbs = nowAbs - offset;
                const std::int64_t bAbs = aAbs - lag;
                if (bAbs < 0) continue;
                const int a = static_cast<int>(aAbs % hybridHistoryLength);
                const int b = static_cast<int>(bAbs % hybridHistoryLength);
                const double al = hybridRawL[static_cast<std::size_t>(a)];
                const double ar = hybridRawR[static_cast<std::size_t>(a)];
                const double bl = hybridRawL[static_cast<std::size_t>(b)];
                const double br = hybridRawR[static_cast<std::size_t>(b)];
                dot += al * bl + ar * br;
                energyA += al * al + ar * ar;
                energyB += bl * bl + br * br;
                ++count;
            }
            if (count >= 3 && energyA > 1.0e-12 && energyB > 1.0e-12) {
                best = std::max(best, dot / std::sqrt(energyA * energyB));
            }
        }
    }
    return std::max(0.0, best);
}

double OptiLabCore::apCoeff(double freq)const{freq=clamp(freq,5.0,sampleRate*0.45);const double t=std::tan(pi*freq/sampleRate);return(t-1.0)/(t+1.0);}
OptiLabCore::Parameters OptiLabCore::defaultParameters(Mode mode)noexcept{Parameters defaults;defaults.mode=mode;defaults.inputDriveDb=mode==Mode::PodcastLeveler?3.5:0.0;return defaults;}
std::pair<double, double> OptiLabCore::processFoundationGuard(
    double preL, double preR, double boostedL, double boostedR
) {
    auto& f = foundationGuard;
    const double lp70L = f.lp70L.run(preL);
    const double lp70R = f.lp70R.run(preR);
    const double lp250L = f.lp250L.run(preL);
    const double lp250R = f.lp250R.run(preR);
    const double lp420L = f.lp420L.run(preL);
    const double lp420R = f.lp420R.run(preR);
    const double lp3700L = f.lp3700L.run(preL);
    const double lp3700R = f.lp3700R.run(preR);

    const double deepL = lp70L;
    const double deepR = lp70R;
    const double usefulL = lp250L - lp70L;
    const double usefulR = lp250R - lp70R;
    const double midL = lp3700L - lp420L;
    const double midR = lp3700R - lp420R;
    const double deepPower = (deepL * deepL + deepR * deepR) * 0.5;
    const double usefulPower = (usefulL * usefulL + usefulR * usefulR) * 0.5;
    const double midPower = (midL * midL + midR * midR) * 0.5;
    const double programDet = std::max(
        absmax2(preL, preR),
        std::max(absmax2(deepL, deepR), std::max(absmax2(usefulL, usefulR), absmax2(midL, midR)))
    );

    if (programDet >= 0.00003) {
        ++f.ageSamples;
    }
    if (!f.primed && programDet > 0.00001) {
        f.deepFast.set(deepPower);
        f.usefulFast.set(usefulPower);
        f.midFast.set(midPower);
        f.deepSlow.set(deepPower);
        f.usefulSlow.set(usefulPower);
        f.midSlow.set(midPower);
        f.primed = true;
    }

    const double fastDeep = f.deepFast.run(deepPower, f.detAttack, f.detRelease);
    const double fastUseful = f.usefulFast.run(usefulPower, f.detAttack, f.detRelease);
    const double fastMid = f.midFast.run(midPower, f.detAttack, f.detRelease);
    const double slowDeep = f.deepSlow.run(deepPower, f.slowAttack, f.slowRelease);
    const double slowUseful = f.usefulSlow.run(usefulPower, f.slowAttack, f.slowRelease);
    const double slowMid = f.midSlow.run(midPower, f.slowAttack, f.slowRelease);

    ++f.controlCounter;
    if (f.controlCounter >= 16) {
        f.controlCounter = 0;

        // Rumble veto: consume the Stream HPF's already-rejected low component.
        // This only gates the new feedback assist; the stock feed-forward bass
        // behavior remains untouched.
        if (f.rumbleCount > 0) {
            const double subEnergy = f.rumbleSubAccum / static_cast<double>(f.rumbleCount);
            const double totalEnergy = f.rumbleTotalAccum / static_cast<double>(f.rumbleCount);
            f.rumbleSubEnv = subEnergy + f.rumbleEnergyTick * (f.rumbleSubEnv - subEnergy);
            f.rumbleTotalEnv = totalEnergy + f.rumbleEnergyTick * (f.rumbleTotalEnv - totalEnergy);
            f.rumbleRatioDb = linToDb(std::sqrt(
                std::max(f.rumbleSubEnv, 1.0e-12) / std::max(f.rumbleTotalEnv, 1.0e-12)
            ));
        }
        f.rumbleSubAccum = f.rumbleTotalAccum = 0.0;
        f.rumbleCount = 0;
        const double rumbleTarget = smoothstep01((f.rumbleRatioDb + 5.0) / 2.0);
        const double rumbleCoeff = rumbleTarget > f.rumbleState ? f.rumbleAttackTick : f.rumbleReleaseTick;
        f.rumbleState = rumbleTarget + rumbleCoeff * (f.rumbleState - rumbleTarget);
        const double rumbleRoom = 1.0 - f.rumbleState;

        // True one-control-block feedback from the existing post-bass 150/420 Hz
        // density split. No extra filter or crossover is run.
        if (f.feedbackCount > 0) {
            const double b1Energy = f.feedbackB1Accum / static_cast<double>(f.feedbackCount);
            const double b2Energy = f.feedbackB2Accum / static_cast<double>(f.feedbackCount);
            f.feedbackRatioDb = linToDb(std::sqrt(
                std::max(b1Energy, 1.0e-12) / std::max(b2Energy, 1.0e-12)
            ));
        }
        f.feedbackB1Accum = f.feedbackB2Accum = 0.0;
        f.feedbackCount = 0;

        double fastDeepBoostDb = 0.0;
        double fastUsefulBoostDb = 0.0;
        double slowDeepBoostDb = 0.0;
        double slowUsefulBoostDb = 0.0;
        double slowDeepCutDb = 0.0;
        double slowUsefulCutDb = 0.0;
        double fastDeepCutDb = 0.0;
        double fastUsefulCutDb = 0.0;
        double slowDeepRatioDb = -120.0;
        double slowUsefulRatioDb = -120.0;

        const auto ratioDb = [](double numerator, double denominator) {
            return OptiLabCore::linToDb(std::sqrt(
                std::max(numerator, 1.0e-12) / std::max(denominator, 1.0e-12)
            ));
        };
        const bool valid = fastMid > 1.0e-12 && programDet >= 0.00003;
        if (valid) {
            const double fd = ratioDb(fastDeep, fastMid);
            const double fu = ratioDb(fastUseful, fastMid);
            const double sd = ratioDb(slowDeep, slowMid);
            const double su = ratioDb(slowUseful, slowMid);
            slowDeepRatioDb = sd;
            slowUsefulRatioDb = su;

            fastDeepBoostDb = (
                4.0 * smoothstep01((-6.2 - fd) / 2.8) +
                3.0 * smoothstep01((-9.0 - fd) / 7.0) +
                0.7 * smoothstep01((-16.0 - fd) / 8.0)
            ) * f.boostScale;
            slowDeepBoostDb = (
                4.0 * smoothstep01((-6.2 - sd) / 2.8) +
                3.0 * smoothstep01((-9.0 - sd) / 7.0) +
                0.7 * smoothstep01((-16.0 - sd) / 8.0)
            ) * f.boostScale;
            fastUsefulBoostDb = (
                3.5 * smoothstep01((-0.35 - fu) / 1.65) +
                2.7 * smoothstep01((-2.0 - fu) / 4.0) +
                1.5 * smoothstep01((-6.0 - fu) / 4.5)
            ) * smoothstep01((-5.8 - fd) / 2.5) * f.boostScale;
            slowUsefulBoostDb = (
                3.5 * smoothstep01((-0.35 - su) / 1.65) +
                2.7 * smoothstep01((-2.0 - su) / 4.0) +
                1.5 * smoothstep01((-6.0 - su) / 4.5)
            ) * smoothstep01((-5.8 - sd) / 2.5) * f.boostScale;

            slowDeepCutDb = (
                4.5 * smoothstep01((sd + 0.3) / 1.0) +
                0.5 * smoothstep01((sd - 0.7) / 2.3)
            ) * f.cutAuthority;
            const double leanPosition = smoothstep01((-0.5 - sd) / 2.0);
            const double usefulCutStart = 1.5 + 2.0 * leanPosition;
            slowUsefulCutDb = 4.5 * smoothstep01((su - usefulCutStart) / 1.5)
                * (0.20 + 0.80 * smoothstep01((su - sd - 0.6) / 1.5))
                * f.cutAuthority;
            slowDeepCutDb = std::max(
                slowDeepCutDb,
                0.90 * slowUsefulCutDb * smoothstep01((sd + 3.0) / 2.5)
            );
            if (f.ageSamples >= f.cutHoldoffSamples) {
                fastDeepCutDb = 5.0 * smoothstep01((fd - 0.5) / 2.2) * f.cutAuthority;
                fastUsefulCutDb = 4.5 * smoothstep01((fu - 3.2) / 1.6)
                    * smoothstep01((fd - 0.0) / 1.4) * f.cutAuthority;
                fastDeepCutDb = std::max(fastDeepCutDb, 0.90 * fastUsefulCutDb);
            }
        }

        const auto follow = [](double current, double target, double attack, double release) {
            return target > current
                ? target + attack * (current - target)
                : target + release * (current - target);
        };
        f.fastDeepBoostEvidenceDb = follow(
            f.fastDeepBoostEvidenceDb, fastDeepBoostDb,
            f.fastBoostAttackTick, f.fastBoostReleaseTick
        );
        f.fastUsefulBoostEvidenceDb = follow(
            f.fastUsefulBoostEvidenceDb, fastUsefulBoostDb,
            f.fastBoostAttackTick, f.fastBoostReleaseTick
        );
        f.fastDeepCutEvidenceDb = follow(
            f.fastDeepCutEvidenceDb, fastDeepCutDb,
            f.fastCutAttackTick, f.fastCutReleaseTick
        );
        f.fastUsefulCutEvidenceDb = follow(
            f.fastUsefulCutEvidenceDb, fastUsefulCutDb,
            f.fastCutAttackTick, f.fastCutReleaseTick
        );

        const double deepBoostTarget = std::max(slowDeepBoostDb, 0.70 * f.fastDeepBoostEvidenceDb);
        const double usefulBoostTarget = std::max(slowUsefulBoostDb, 0.70 * f.fastUsefulBoostEvidenceDb);
        const double deepCutTarget = std::max(slowDeepCutDb, 0.95 * f.fastDeepCutEvidenceDb);
        const double usefulCutTarget = std::max(slowUsefulCutDb, 0.95 * f.fastUsefulCutEvidenceDb);
        const double globalCutTarget = std::max(deepCutTarget, usefulCutTarget);

        f.deepBoostStateDb = follow(
            f.deepBoostStateDb, deepBoostTarget, f.boostAttackTick,
            globalCutTarget > 0.60 ? f.boostSuppressTick : f.boostReleaseTick
        );
        f.usefulBoostStateDb = follow(
            f.usefulBoostStateDb, usefulBoostTarget, f.boostAttackTick,
            globalCutTarget > 0.60 ? f.boostSuppressTick : f.boostReleaseTick
        );
        f.deepCutStateDb = follow(
            f.deepCutStateDb, deepCutTarget, f.cutAttackTick,
            deepBoostTarget > 2.0 ? f.cutSuppressTick : f.cutReleaseTick
        );
        f.usefulCutStateDb = follow(
            f.usefulCutStateDb, usefulCutTarget, f.cutAttackTick,
            usefulBoostTarget > 2.0 ? f.cutSuppressTick : f.cutReleaseTick
        );

        const double deepRaw = f.deepBoostStateDb - f.deepCutStateDb;
        const double usefulRaw = f.usefulBoostStateDb - f.usefulCutStateDb;
        if (deepRaw * usefulRaw >= 0.0) {
            if (std::abs(deepRaw) >= std::abs(usefulRaw)) {
                f.deepTargetDb = deepRaw + (usefulRaw - deepRaw) * (0.08 * f.link);
                f.usefulTargetDb = usefulRaw + (deepRaw - usefulRaw) * (0.70 * f.link);
            } else {
                f.usefulTargetDb = usefulRaw + (deepRaw - usefulRaw) * (0.08 * f.link);
                f.deepTargetDb = deepRaw + (usefulRaw - deepRaw) * (0.70 * f.link);
            }
        } else {
            const double shared = (deepRaw + usefulRaw) * 0.5;
            f.deepTargetDb = deepRaw + (shared - deepRaw) * (0.10 * f.link);
            f.usefulTargetDb = usefulRaw + (shared - usefulRaw) * (0.10 * f.link);
        }
        // Closed-loop foundation refinement. Only moderate lean cases may ask
        // for extra foundation; strong existing boosts, cut cases, dense bass
        // activity, and persistent sub-rumble all reduce or veto that request.
        const double feedbackEligible = valid && f.ageSamples >= static_cast<std::size_t>(std::floor(sampleRate * 5.0 + 0.5)) ? 1.0 : 0.0;
        const double feedbackModerate = smoothstep01((f.deepTargetDb - 0.8) / 1.0)
                                      * (1.0 - smoothstep01((f.deepTargetDb - 3.4) / 0.8));
        const double feedbackDeepLean = 1.0 - smoothstep01((slowDeepRatioDb + 4.5) / 1.5);
        const double feedbackBodyLean = smoothstep01((-1.0 - slowUsefulRatioDb) / 0.6);
        const double feedbackNoCut = 1.0 - smoothstep01(globalCutTarget / 0.25);
        const double feedbackPostRoom = 1.0 - smoothstep01((f.feedbackRatioDb - 3.2) / 0.8);
        const double feedbackPostExcess = smoothstep01((f.feedbackRatioDb - 3.0) / 2.0);
        const double burdenCoeff = feedbackPostExcess > f.feedbackBurden
            ? f.feedbackBurdenAttackTick : f.feedbackBurdenReleaseTick;
        f.feedbackBurden = feedbackPostExcess + burdenCoeff * (f.feedbackBurden - feedbackPostExcess);
        const double feedbackActivityRoom = (1.0 - smoothstep01((f.feedbackBurden - 0.30) / 0.45))
                                          * (1.0 - smoothstep01((finalFoundationBurden - 0.15) / 0.65));

        const double feedbackRequestDb = f.feedbackMaxAssistDb
            * feedbackEligible
            * feedbackModerate
            * feedbackDeepLean
            * feedbackBodyLean
            * feedbackNoCut
            * feedbackPostRoom
            * feedbackActivityRoom
            * rumbleRoom;

        const bool feedbackForceRelease = !valid
            || globalCutTarget > 0.10
            || slowDeepRatioDb > -3.5
            || slowUsefulRatioDb > -0.20
            || f.feedbackBurden > 0.62
            || f.rumbleState > 0.50
            || finalFoundationBurden > 0.18;
        const double feedbackCoeff = feedbackRequestDb > f.feedbackServoDb
            ? f.feedbackAttackTick
            : feedbackForceRelease ? f.feedbackFastReleaseTick : f.feedbackReleaseTick;
        f.feedbackServoDb = feedbackRequestDb + feedbackCoeff * (f.feedbackServoDb - feedbackRequestDb);
        f.deepTargetDb += f.feedbackServoDb;

        f.deepTargetGain = dbToLin(f.deepTargetDb);
        f.usefulTargetGain = dbToLin(f.usefulTargetDb);
        const double withdrawPosition = smoothstep01(clamp(globalCutTarget / 3.5, 0.0, 1.0));
        f.voiceTarget = 1.0 - clamp(f.withdrawAuthority * withdrawPosition, 0.0, 1.0);
    }

    const double voiceCoeff = f.voiceTarget < f.voiceGain ? f.voiceWithdraw : f.voiceReturn;
    f.voiceGain = f.voiceTarget + voiceCoeff * (f.voiceGain - f.voiceTarget);
    const double voicedL = preL + (boostedL - preL) * f.voiceGain;
    const double voicedR = preR + (boostedR - preR) * f.voiceGain;

    ++f.coefficientCounter;
    if (f.coefficientCounter >= 64) {
        f.coefficientCounter = 0;
        double bodyDb = 0.0;
        double bodyFreq = 90.0;
        double bodyQ = 1.10;
        if (f.usefulTargetDb >= 0.0) {
            bodyDb = std::min(3.0, f.usefulTargetDb * 0.50);
        } else {
            bodyDb = -std::min(4.5, std::max(0.0, -f.usefulTargetDb - 1.5) * 1.50);
            bodyFreq = 125.0;
            bodyQ = 0.85;
        }
        f.shelfL.setLowShelf(70.0, 1.0, f.deepTargetDb, sampleRate);
        f.shelfR.copyCoefficientsFrom(f.shelfL);
        f.bodyL.setPeak(bodyFreq, bodyQ, bodyDb, sampleRate);
        f.bodyR.copyCoefficientsFrom(f.bodyL);
    }

    return {
        f.bodyL.run(f.shelfL.run(voicedL)),
        f.bodyR.run(f.shelfR.run(voicedR))
    };
}

OptiLabCore::Activity OptiLabCore::activity()const noexcept{return{std::min(currentAgcLowEffGain,currentAgcHighEffGain),currentDensityGain,currentBand6Gain,currentBand6ControlGain,currentFinalGain,foundationGuard.feedbackServoDb,-linToDb(finalThresholdDriveTarget),linToDb(agcTarget),finalBackoffDb};}
void OptiLabCore::prepare(double newSampleRate){sampleRate=std::isfinite(newSampleRate)&&newSampleRate>=8000.0&&newSampleRate<=768000.0?newSampleRate:48000.0;lastMode=-1;applyModeAndDerivedParameters();reset();}
void OptiLabCore::setParameters(const Parameters& newParameters){const int previousMode=static_cast<int>(params.mode);params=newParameters;params.autoAdaptPct=clamp(params.autoAdaptPct,0.0,100.0);params.inputDriveDb=clamp(params.inputDriveDb,-12.0,18.0);const int nextMode=static_cast<int>(params.mode);if(lastMode>=0&&previousMode!=nextMode){params.inputDriveDb=nextMode==0?3.5:0.0;reset();}applyModeAndDerivedParameters();lastMode=nextMode;}
void OptiLabCore::resetPhaseState(){for(auto&ap:apL)ap.reset();for(auto&ap:apR)ap.reset();}
void OptiLabCore::reset(){agcLiftStateDb=0.0;finalBackoffDb=0.0;finalFoundationBurden=0.0;finalLoadCounter=0;agcTarget=dbToLin(agcTargetBaseDb);agcLGain=agcHGain=1.0;startupActivity=gateProgEnv=gateState=gateClosedMemory=gateReopenEnv=gateReopenPulse=0.0;adaptBassGain=1.0;adaptTopPresenceGain=adaptTopAirGain=1.0;currentAgcLowEffGain=currentAgcHighEffGain=currentDensityGain=currentBand6Gain=currentBand6ControlGain=currentFinalGain=1.0;finalThresholdDriveS=finalThresholdDriveTarget>0.0?finalThresholdDriveTarget:1.0;finalThresholdGuardGain=1.0;preclip.gain=1.0;masterStartupArmed=1;masterStartupAge=0;masterCatchGain=1.0;foundationGuard.reset();hp30L.reset();hp30R.reset();resetPhaseState();agcLpL.reset();agcLpR.reset();agcLowEnv.e=agcHighEnv.e=0.0;postAgcRoundL.reset();postAgcRoundR.reset();masterRawEnv.e=masterAmpEnv.e=masterCatchEnv.e=0.0;adaptBassLpL.reset();adaptBassLpR.reset();adaptBassEnv.e=adaptProgEnv.e=0.0;bassclipSplitL.reset();bassclipSplitR.reset();bassclipHpfL.reset();bassclipHpfR.reset();bassclipPreL.reset();bassclipPreR.reset();for(auto&f:xbL)f.reset();for(auto&f:xbR)f.reset();adaptTopAirHpL.reset();adaptTopAirHpR.reset();adaptTopEdgeEnv.e=adaptTopEdgeProgEnv.e=adaptTopAirEnv.e=adaptTopAirProgEnv.e=0.0;for(auto&l:lim){l.env=0.0;l.gain=1.0;}for(auto&e:mbEvent){e.env=0.0;e.gain=1.0;}shapeRecoveryCounter=0;shapeRecoveryTick=false;shapeBlockCounter=0;shapeCompRecoveryDb.fill(0.0);shapeLimiterRecoveryDb.fill(0.0);compRecoveryGain.fill(1.0);limiterRecoveryGain.fill(1.0);shapeCompRatioBlock.fill(1.0);shapeLimiterRatioBlock.fill(1.0);shapeLevel.fill(0.0);shapeServoDb.fill(0.0);shapeServoGain.fill(1.0);shapePowerAccum.fill(0.0);for(auto&c:mbClipL)c.reset();for(auto&c:mbClipR)c.reset();ubFast4.reset();ubFast5.reset();ubFast6.reset();ubSlow4.reset();ubSlow5.reset();ubSlow6.reset();ubDslow4.reset();ubDslow5.reset();ubDslow6.reset();ubCslow4.reset();ubCslow5.reset();ubCslow6.reset();ubGate4.e=ubGate5.e=ubGate6.e=0.0;ubLim6.gain=1.0;usPrev4L=usPrev4R=usPrev24L=usPrev24R=usPrev5L=usPrev5R=usPrev25L=usPrev25R=usPrev6L=usPrev6R=usPrev26L=usPrev26R=0.0;postXt2RoundL.reset();postXt2RoundR.reset();finalFullEnv.e=0.0;distLpfL.reset();distLpfR.reset();finalRoundL.reset();finalRoundR.reset();fcsResL.reset();fcsResR.reset();widthMidFast=widthMidSlow=widthMidEnv=widthSideEnv=widthAdaptiveGain=0.0;deliveryWrite=0;deliveryGain=1.0;deliveryBufL.fill(0.0);deliveryBufR.fill(0.0);deliveryRequired.fill(1.0);deliveryHistL.fill(0.0);deliveryHistR.fill(0.0);hybridWrite=hybridEnergyWrite=hybridEnergyCount=0;hybridSampleClock=0;hybridCandidateActivePrev=false;hybridEventStartAbs=-1;hybridEventStartRing=0;hybridEventCorrelation=0.0;hybridOnset1=hybridOnset2=hybridOnset3=-1000000000LL;hybridRefEnergySum=hybridDeltaEnergySum=0.0;hybridBurdenAccept=hybridLimiterGain=1.0;hybridLimiterActiveCount=0;hybridLimiterWindowTracked=false;
    std::fill(hybridRequiredActive.begin(),hybridRequiredActive.end(),std::uint8_t{0});std::fill(hybridRawL.begin(),hybridRawL.end(),0.0);std::fill(hybridRawR.begin(),hybridRawR.end(),0.0);std::fill(hybridCandidateL.begin(),hybridCandidateL.end(),0.0);std::fill(hybridCandidateR.begin(),hybridCandidateR.end(),0.0);std::fill(hybridShavedL.begin(),hybridShavedL.end(),0.0);std::fill(hybridShavedR.begin(),hybridShavedR.end(),0.0);std::fill(hybridRequiredGain.begin(),hybridRequiredGain.end(),1.0);std::fill(hybridBurden.begin(),hybridBurden.end(),1.0);std::fill(hybridEventGate.begin(),hybridEventGate.end(),0.0);std::fill(hybridWorkLimit.begin(),hybridWorkLimit.end(),1.0);std::fill(hybridMakeup.begin(),hybridMakeup.end(),1.0);std::fill(hybridRefEnergy.begin(),hybridRefEnergy.end(),0.0);std::fill(hybridDeltaEnergy.begin(),hybridDeltaEnergy.end(),0.0);fcsBufL.fill(0.0);fcsBufR.fill(0.0);fcsBufOL.fill(0.0);fcsBufOR.fill(0.0);for(auto&band:snubL)band.fill(0.0);for(auto&band:snubR)band.fill(0.0);masterBufL.fill(0.0);masterBufR.fill(0.0);fcsWrite=snubWrite=masterWrite=0;}

void OptiLabCore::applyModeAndDerivedParameters(){
    const int coreMode=static_cast<int>(params.mode);const double autoUp=clamp(params.autoAdaptPct*0.01,0.0,1.0);band6OwnDetectorMix=streamAgcLiftDb=finalBackoffMix=0.0;
    if(coreMode==0){inputTrimDb=3.5;phaseRotatePct=3;subsonicHpf=1;agcAmountPct=65;agcDriveDb=.5;releaseTime=7;pdReleasePct=70;gateThresholdDb=-20;gateReopenSpeedMs=40;gateReopenStrengthPct=65;postAgcSmoothDrivePct=25;bassCouplingPct=70;bassEqDb=2;bassScReliefPct=35;lowBassFloorPct=15;lowCoherencePct=65;lowReleaseStabPct=70;transitionFillPct=18;adaptiveBassCouplingPct=12;bassClipPct=8;bassClipDensityPct=0;densityDb=0;xt2AmountPct=100;presenceDb=2;brillianceDb=2;adaptiveTopCouplingPct=50;crossoverModel=2;mbClipPct=0;mbShapePct=0;mbLimiterDepthPct=50;mbCompLimiterPct=0;clipDriveDb=0;recombControlPct=0;dcCancelPct=65;upperSnubberPct=0;snubberLookaheadMs=1.5;postXt2SmoothDrivePct=10;stereoMode=0;stereoWidthPct=100;preFinalDriveDb=-1.5;clipperStyle=0;preLimiterPct=100;clipRestraintPct=100;overshootPct=100;lookaheadMs=.36+(1.50-.36)*smoothstep01((autoUp-.70)/.30);finalThresholdDb=-1.5;finalThresholdMakeupPct=100;clipCeilingDb=-.1;topFilterMode=2;outputTrimDb=0;smoothDriveRounderPct=58;
        agcAmountPct=65+(85-65)*autoUp;agcDriveDb=.5+(0-.5)*autoUp;releaseTime=7+(5.2-7)*(autoUp*autoUp);pdReleasePct=70+(84-70)*autoUp;gateReopenSpeedMs=40+(36-40)*autoUp;gateReopenStrengthPct=65+(60-65)*(autoUp*autoUp);bassScReliefPct=35+(56-35)*autoUp;lowReleaseStabPct=70+(82-70)*autoUp;adaptiveBassCouplingPct=12+(22-12)*autoUp;adaptiveTopCouplingPct=50+(72-50)*autoUp;postXt2SmoothDrivePct=10+(12-10)*autoUp;clipDriveDb=0+(-.7-0)*autoUp;
    }else if(coreMode==1){inputTrimDb=0;phaseRotatePct=5;subsonicHpf=0;agcAmountPct=56;agcDriveDb=0;bassCouplingPct=50;releaseTime=5;gateThresholdDb=-30;gateReopenSpeedMs=50;gateReopenStrengthPct=55;densityDb=3.5;xt2AmountPct=84;bassEqDb=3.6;presenceDb=2.3;brillianceDb=3.2;clipDriveDb=-.8;clipperStyle=2;preLimiterPct=44;clipRestraintPct=38;clipCeilingDb=-.1;finalThresholdDb=-.8;finalThresholdMakeupPct=100;stereoMode=0;stereoWidthPct=100;topFilterMode=0;outputTrimDb=1.1;mbClipPct=16;dcCancelPct=46;overshootPct=100;recombControlPct=10;lookaheadMs=.54;crossoverModel=2;mbShapePct=0;mbLimiterDepthPct=50;mbCompLimiterPct=0;pdReleasePct=78;bassScReliefPct=76;lowCoherencePct=66;lowReleaseStabPct=74;transitionFillPct=12;lowBassFloorPct=42;adaptiveBassCouplingPct=65;adaptiveTopCouplingPct=50;bassClipPct=32;bassClipDensityPct=6;upperSnubberPct=20;snubberLookaheadMs=.73+(1.50-.73)*smoothstep01((autoUp-.65)/.35);postAgcSmoothDrivePct=12;postXt2SmoothDrivePct=12;preFinalDriveDb=-.4;smoothDriveRounderPct=50;
        const double widthStage=smoothstep01((autoUp-0.40)/0.60);const double bassPressureStage=smoothstep01((autoUp-0.18)/(0.82-0.18));const double agcPressureStage=smoothstep01((autoUp-0.35)/(0.88-0.35));const double finalHandoff=smoothstep01((autoUp-0.50)/0.50);agcAmountPct=56+(50-56)*agcPressureStage;agcDriveDb=0.2*agcPressureStage;releaseTime=5+(6.1-5)*agcPressureStage;pdReleasePct=78;gateThresholdDb=-30-5*agcPressureStage;gateReopenStrengthPct=55;postAgcSmoothDrivePct=12+2*agcPressureStage;bassCouplingPct=50+(60-50)*bassPressureStage;bassEqDb=3.6;bassScReliefPct=76;lowBassFloorPct=42;lowCoherencePct=66+(82-66)*bassPressureStage;lowReleaseStabPct=74;adaptiveBassCouplingPct=65;bassClipPct=32+(40-32)*bassPressureStage;stereoWidthPct=100+50*widthStage;const double densityForkStage=smoothstep01((autoUp-0.50)/(0.78-0.50));const double broadcastShapeStage=smoothstep01((autoUp-0.50)/(0.80-0.50));const double legacyDensityDb=3.5+(3.8-3.5)*autoUp;densityDb=legacyDensityDb+(3.2-legacyDensityDb)*densityForkStage;mbClipPct=16+(24-16)*densityForkStage;mbCompLimiterPct=60*densityForkStage;mbShapePct=100*broadcastShapeStage;dcCancelPct=46+(18-46)*finalHandoff;upperSnubberPct=20+(68-20)*finalHandoff;postXt2SmoothDrivePct=12+(20-12)*finalHandoff;preFinalDriveDb=-.4+.4*finalHandoff;outputTrimDb=1.1*(1-finalHandoff);preLimiterPct=44+2*finalHandoff;clipRestraintPct=38-12*finalHandoff;finalStyleBlend=finalHandoff;finalThresholdDb=-.8+(-1.4+.8)*finalHandoff;lookaheadMs=.54+(1.50-.54)*smoothstep01((autoUp-.65)/.35);smoothDriveRounderPct=(50+(54-50)*autoUp)*(1-finalHandoff);
    }else{inputTrimDb=0;phaseRotatePct=0;subsonicHpf=0;agcAmountPct=0;agcDriveDb=0;releaseTime=6.5;pdReleasePct=0;gateThresholdDb=-70;gateReopenSpeedMs=50;gateReopenStrengthPct=0;postAgcSmoothDrivePct=0;bassCouplingPct=0;bassEqDb=0;bassScReliefPct=0;lowBassFloorPct=0;lowCoherencePct=0;lowReleaseStabPct=0;transitionFillPct=0;adaptiveBassCouplingPct=0;bassClipPct=25;bassClipDensityPct=0;densityDb=-.4;xt2AmountPct=10;presenceDb=0;brillianceDb=0;adaptiveTopCouplingPct=0;crossoverModel=2;mbClipPct=20;mbShapePct=0;mbLimiterDepthPct=50;mbCompLimiterPct=0;clipDriveDb=0;recombControlPct=6;dcCancelPct=0;upperSnubberPct=32;snubberLookaheadMs=1.5;postXt2SmoothDrivePct=12;stereoMode=0;stereoWidthPct=100;preFinalDriveDb=-1.6;clipperStyle=0;preLimiterPct=100;clipRestraintPct=60;overshootPct=100;lookaheadMs=.73;finalThresholdDb=-2;finalThresholdMakeupPct=100;clipCeilingDb=-.1;topFilterMode=0;outputTrimDb=0;smoothDriveRounderPct=50;densityDb=-.4+(-.8+.4)*autoUp;snubberLookaheadMs=1.5+(2.0-1.5)*autoUp;postXt2SmoothDrivePct=12+(20-12)*autoUp;preFinalDriveDb=-1.6+(-3.0+1.6)*autoUp;clipDriveDb=0+(-.6)*autoUp;lookaheadMs=.73+(1.5-.73)*autoUp;finalThresholdDb=-2+(-3.0+2)*autoUp;smoothDriveRounderPct=0;}
    if(coreMode==1){const double finalHandoff=smoothstep01((autoUp-.50)/.50),densityForkStage=smoothstep01((autoUp-.50)/(.78-.50));streamAgcLiftDb=3.0*finalHandoff;finalBackoffMix=finalHandoff;band6OwnDetectorMix=densityForkStage;}
    processorMode=coreMode==2?1:0;inputTrimDb=clamp(params.inputDriveDb,-12.0,18.0);adaptiveTopCouplingPct=clamp(adaptiveTopCouplingPct,0.0,100.0);outputTrimDb=clamp(outputTrimDb,-12.0,3.0);
    inputGain=dbToLin(inputTrimDb);agcDrive=dbToLin(agcDriveDb);const double densityPosDb=std::max(densityDb,0.0),densityNegDb=std::min(densityDb,0.0);densityAudioGain=dbToLin(densityNegDb+densityPosDb*.35);densityDetectorGain=dbToLin(densityPosDb*.65);densityClipDrive=dbToLin(densityPosDb*.55);presenceGain=dbToLin(presenceDb);brillianceGain=dbToLin(brillianceDb);clipDriveMb=dbToLin(clipDriveDb*.60);clipDriveFull=dbToLin(clipDriveDb*.25);ceiling=dbToLin(clipCeilingDb);broadcastDensityActive=coreMode==1&&(mbCompLimiterPct>0.000001||mbShapePct>0.000001);mbShape=clamp(mbShapePct,0.0,100.0)*0.01;shapeHighAmount=std::max(0.0,(mbShape-0.35)/0.65);shapeHighAmount*=shapeHighAmount;const double mbCompLimiterRaw=clamp(mbCompLimiterPct,0.0,100.0)*0.01;mbCompLimiter=mbCompLimiterRaw*(0.85+0.15*mbCompLimiterRaw);mbCompKeep=1.0-mbCompLimiter;finalThresholdDb=clamp(finalThresholdDb,-24,6);finalThresholdMakeupPct=clamp(finalThresholdMakeupPct,0,100);finalThresholdDriveTarget=dbToLin(-finalThresholdDb);finalThresholdMakeup=finalThresholdMakeupPct*.01;smoothDriveRounderAmt=clamp(smoothDriveRounderPct,0,100)*.01;postAgcSmoothDriveAmt=clamp(postAgcSmoothDrivePct,0,25)*.01;postXt2SmoothDriveAmt=clamp(postXt2SmoothDrivePct,0,50)*.01;postAgcSmoothRecoveryGain=dbToLin(2.0*clamp(postAgcSmoothDrivePct,0,25)/25.0);postXt2SmoothRecoveryGain=dbToLin(2.0*clamp(postXt2SmoothDrivePct,0,50)/50.0);preFinalDriveGain=dbToLin(clamp(preFinalDriveDb,-12,12));outputGain=dbToLin(outputTrimDb);mbClipMix=mbClipPct*.01;dcCancel=dcCancelPct*.01;dc3Amt=dcCancel*.35;dc4Amt=dcCancel*.55;dc5Amt=dcCancel*.78;dc6Amt=dcCancel*.92;overshootAmt=overshootPct*.01;recombControl=recombControlPct*.01;crossoverModel=static_cast<int>(std::floor(clamp(crossoverModel,0,3)+.5));pdRelease=pdReleasePct*.01;upperSnubber=upperSnubberPct*.01;gateReopenStrength=gateReopenStrengthPct*.01;const double gateReopenSpeedSec=std::max(gateReopenSpeedMs*.001,.005);snubberLookaheadMs=clamp(snubberLookaheadMs,0,1.50);lookaheadMs=clamp(lookaheadMs,0,1.50);subsonicHpf=static_cast<int>(std::floor(clamp(subsonicHpf,0,1)+.5));topFilterMode=static_cast<int>(std::floor(clamp(topFilterMode,0,3)+.5));effectiveSnubberLookahead=(upperSnubber>0&&snubberLookaheadMs>0)?std::min(snubBufferLength-1,static_cast<int>(std::floor(sampleRate*snubberLookaheadMs*.001+.5))):0;effectiveFinalLookahead=(overshootAmt>0&&lookaheadMs>0)?std::min(fcsBufferLength-1,static_cast<int>(std::floor(sampleRate*lookaheadMs*.001+.5))):0;deliveryTarget=ceiling*dbToLin(-0.075);deliveryLookaheadSamples=std::min(deliveryBufferLength-2,static_cast<int>(std::floor(sampleRate*.00150+.5)));deliveryAnticipationSamples=std::max(1,deliveryLookaheadSamples-deliveryDetectorDelaySamples);deliveryRelease=std::exp(-1.0/std::max(1.0,sampleRate*.030));hybridClassificationSamples=coreMode==1?std::min(hybridHistoryLength-2,(int)std::floor(sampleRate*0.00150+0.5)):(coreMode==2?std::min(hybridHistoryLength-2,(int)std::floor(sampleRate*0.00200+0.5)):0);
    hybridLimiterLookaheadSamples=(coreMode==1||coreMode==2)?std::min(hybridHistoryLength-2,(int)std::floor(sampleRate*0.00200+0.5)):0;
    hybridTotalDelaySamples=(coreMode==1||coreMode==2)?std::min(hybridHistoryLength-2,hybridClassificationSamples+hybridLimiterLookaheadSamples):0;
    hybridBurdenWindowSamples=std::max(1,std::min(hybridEnergyLength-1,(int)std::floor(sampleRate*0.008+0.5)));
    hybridPeriodMinSamples=std::max(2,(int)std::floor(sampleRate*0.00025+0.5));
    hybridPeriodMaxSamples=std::max(hybridPeriodMinSamples+1,std::min(hybridHistoryLength/3,(int)std::floor(sampleRate*0.020+0.5)));
    hybridBurdenAttack=std::exp(-1.0/std::max(1.0,sampleRate*0.00025));hybridBurdenRelease=std::exp(-1.0/std::max(1.0,sampleRate*0.008));hybridLimiterRelease=std::exp(-1.0/std::max(1.0,sampleRate*0.030));
    std::fill(hybridAttackShape.begin(),hybridAttackShape.end(),1.0);if(hybridLimiterLookaheadSamples>0){const double inv=1.0/hybridLimiterLookaheadSamples;for(int d=0;d<=hybridLimiterLookaheadSamples;++d){const double u=d*inv;hybridAttackShape[(std::size_t)d]=u*u*(3.0-2.0*u);}}else hybridAttackShape[0]=0.0;
    masteringLookaheadSamples=processorMode==1?std::min(masterBufferLength-1,static_cast<int>(std::floor(sampleRate*.010+.5))):0;masterStartupPrimeWindow=static_cast<int>(std::floor(sampleRate*.350+.5));masterStartupActiveThresh=dbToLin(-70);pathDelay=static_cast<std::size_t>(masteringLookaheadSamples+effectiveSnubberLookahead+effectiveFinalLookahead+hybridTotalDelaySamples+deliveryLookaheadSamples);
    phaseMode=static_cast<int>(std::floor(clamp(phaseRotatePct,0,6)+.5));if(phaseMode!=phaseModeLast){resetPhaseState();phaseModeLast=phaseMode;}phaseStages=phaseMode==1?2:phaseMode==2?4:phaseMode==3?6:phaseMode==4?8:phaseMode==5?10:phaseMode==6?12:0;const std::array<double,12> phaseFreqs{55,85,130,200,310,480,740,1150,1800,2800,4300,6500};for(std::size_t i=0;i<apC.size();++i)apC[i]=apCoeff(phaseFreqs[i]);
    agcMix=agcAmountPct*.01;agcDownMix=agcMix<=.50?agcMix:.50+(agcMix-.50)*.40;xt2Mix=xt2AmountPct*.01;adaptiveTopCoupling=adaptiveTopCouplingPct*.01;bassCoupling=bassCouplingPct*.01;bassScRelief=bassScReliefPct*.01;lowCoherence=lowCoherencePct*.01;lowReleaseStab=lowReleaseStabPct*.01;transitionFill=transitionFillPct*.01;lowBassFloor=lowBassFloorPct*.01;adaptiveBassCoupling=adaptiveBassCouplingPct*.01;foundationMix=coreMode==1?smoothstep01((autoUp-0.18)/(0.82-0.18)):0.0;streamHpfMix=coreMode==1?smoothstep01((autoUp-0.50)/(0.80-0.50)):0.0;hybridMix=coreMode==1?smoothstep01((autoUp-0.50)/0.50):(coreMode==2?1.0:0.0);bassClip=bassClipPct*.01;bassClipDensity=bassClipDensityPct*.01;prelimitMix=preLimiterPct*.01;clipRestraint=clipRestraintPct*.01;peakOnlyFinalLimiter=clipperStyle==0&&preLimiterPct>=99&&clipRestraintPct>=99&&smoothDriveRounderPct<=.001&&postAgcSmoothDrivePct<=.001&&postXt2SmoothDrivePct<=.001&&std::abs(preFinalDriveDb)<=.001&&topFilterMode==0&&outputTrimDb==0&&finalThresholdDb>=-.001&&finalThresholdDb<=.001;prelimitThresh=peakOnlyFinalLimiter?ceiling:ceiling*.985;fcsThreshSetting=peakOnlyFinalLimiter?ceiling:ceiling*.985;
    agcEnvAttack=std::exp(-1/(sampleRate*.045));agcGainAttack=std::exp(-1/(sampleRate*.030));agcRelease=std::exp(-1/(sampleRate*(.080+releaseTime*.085)));agcReleaseSlow=std::exp(-1/(sampleRate*(.240+releaseTime*.150)));bandAttack=std::exp(-1/(sampleRate*.0012));upperBandAttack=std::exp(-1/(sampleRate*.0024));upperMidBandAttack=std::exp(-1/(sampleRate*.0018));bandRelease=std::exp(-1/(sampleRate*(.035+releaseTime*.035)));bandReleaseSlow=std::exp(-1/(sampleRate*(.100+releaseTime*.080)));const double lowBandReleaseBase=std::exp(-1/(sampleRate*(.060+releaseTime*.055))),lowBandReleaseSlow2=std::exp(-1/(sampleRate*(.180+releaseTime*.100)));lowBandRelease=bandRelease*(1-lowReleaseStab)+lowBandReleaseBase*lowReleaseStab;lowBandReleaseSlow=bandReleaseSlow*(1-lowReleaseStab)+lowBandReleaseSlow2*lowReleaseStab;clipAttack=std::exp(-1/(sampleRate*.0008));clipRelease=std::exp(-1/(sampleRate*.045));finalThresholdSmooth=std::exp(-1/(sampleRate*.010));recombAttack=std::exp(-1/(sampleRate*.0007));recombRelease=std::exp(-1/(sampleRate*(.090+releaseTime*.055)));startupActivityRelease=std::exp(-1/(sampleRate*.350));masterCatchAttack=std::exp(-1/(sampleRate*.010));masterCatchRelease=std::exp(-1/(sampleRate*.150));masterEnvAttack=std::exp(-1/(sampleRate*.006));masterEnvRelease=std::exp(-1/(sampleRate*.320));gateDetectorRelease=std::exp(-1/(sampleRate*.160));gateCloseCoeff=std::exp(-1/(sampleRate*(.040+releaseTime*.012)));gateOpenCoeff=std::exp(-1/(sampleRate*.0015));gateAgcFreezeRelease=std::exp(-1/(sampleRate*8.0));gateXt2FreezeRelease=std::exp(-1/(sampleRate*2.5));gateReopenRelease=std::exp(-1/(sampleRate*gateReopenSpeedSec));gateReopenEnvRelease=std::exp(-1/(sampleRate*std::max(gateReopenSpeedSec*.85,.005)));gateReopenDecay=std::exp(-1/(sampleRate*std::max(gateReopenSpeedSec*4.5,.120)));gateReopenPulseScale=.20+.95*gateReopenStrength;gateAgcDriftTarget=dbToLin(-10);gateAgcDriftCoeff=std::exp(-1/(sampleRate*4.5));upperSnubFastA=1-std::exp(-1/(sampleRate*.00055));upperSnubSlowA=1-std::exp(-1/(sampleRate*.018));upperSnubDeltaA=1-std::exp(-1/(sampleRate*.0030));upperSnubCurveA=1-std::exp(-1/(sampleRate*.0022));upperSnubGainAttack=std::exp(-1/(sampleRate*.00010));upperSnubGainRelease=std::exp(-1/(sampleRate*.0028));hpf30A=1-std::exp(-2*pi*(coreMode==1?42.5:20.0)/sampleRate);agcSplitA=1-std::exp(-2*pi*200/sampleRate);x1A=1-std::exp(-2*pi*150/sampleRate);x2A=1-std::exp(-2*pi*420/sampleRate);x3A=1-std::exp(-2*pi*700/sampleRate);x4A=1-std::exp(-2*pi*1600/sampleRate);x5A=1-std::exp(-2*pi*3700/sampleRate);distCancelA=1-std::exp(-2*pi*2200/sampleRate);agcTarget=dbToLin(-17);agcMaxGain=dbToLin(coreMode==1?14.0:9.0);agcMinGain=dbToLin(-14);gateLin=dbToLin(gateThresholdDb);
    agcTargetBaseDb=-17.0;if(finalBackoffMix<=.0000001)finalBackoffDb=0.0;finalBackoffDb=clamp(finalBackoffDb,0.0,2.0*finalBackoffMix);finalFoundationBurden=clamp(finalBackoffDb/.60,0.0,1.0);agcLiftStateDb=clamp(agcLiftStateDb,0.0,streamAgcLiftDb);agcTarget=dbToLin(agcTargetBaseDb+agcLiftStateDb-.35*finalBackoffDb);finalThresholdDriveTarget=dbToLin(-std::min(0.0,finalThresholdDb+.90*finalBackoffDb));agcLiftAttackBlock=std::exp(-64.0/std::max(1.0,sampleRate*6.0));agcLiftReleaseBlock=std::exp(-64.0/std::max(1.0,sampleRate*1.5));finalBackoffAttackBlock=std::exp(-64.0/std::max(1.0,sampleRate*1.8));finalBackoffReleaseBlock=std::exp(-64.0/std::max(1.0,sampleRate*8.0));
    const std::array<double,6> baseThresholdDb{-9.5,-11.5,-13.0,-14.5,-16.5,-18.0};
    if(broadcastDensityActive){
        const double limiterDepthUser=clamp(mbLimiterDepthPct*0.01,0.0,1.0);
        const double limiterDepthNormal=0.75*std::sqrt(limiterDepthUser);
        const double limiterDepthDropDb=8.0*limiterDepthNormal*limiterDepthNormal;
        const double limiterFlatDb=-8.0-16.0*limiterDepthNormal*limiterDepthNormal;
        std::array<double,6> limiterNaturalDb{};
        for(std::size_t i=0;i<6;++i)limiterNaturalDb[i]=baseThresholdDb[i]-limiterDepthDropDb;
        limiterWorkDb[0]=limiterNaturalDb[0]+(limiterFlatDb-limiterNaturalDb[0])*mbShape;
        limiterWorkDb[1]=limiterNaturalDb[1]+(limiterFlatDb-limiterNaturalDb[1])*mbShape;
        limiterWorkDb[2]=limiterNaturalDb[2]+(limiterFlatDb-limiterNaturalDb[2])*mbShape;
        const double limiterControl4Db=limiterNaturalDb[3]+(limiterFlatDb-limiterNaturalDb[3])*(shapeHighAmount*0.34);
        const double limiterControl5Db=baseThresholdDb[4]-limiterDepthDropDb*0.18;
        const double limiterControl6Db=baseThresholdDb[5]-limiterDepthDropDb*0.18;
        limiterWorkDb[3]=limiterNaturalDb[3]+(limiterControl4Db-limiterNaturalDb[3])*shapeHighAmount;
        limiterWorkDb[4]=limiterNaturalDb[4]+(limiterControl5Db-limiterNaturalDb[4])*shapeHighAmount;
        limiterWorkDb[5]=limiterNaturalDb[5]+(limiterControl6Db-limiterNaturalDb[5])*shapeHighAmount;
        for(std::size_t i=0;i<6;++i){limiterWork[i]=dbToLin(limiterWorkDb[i]);limiterQuietThreshold[i]=limiterWork[i]*(1.0-1.0e-12);}
        mbPresencePost=dbToLin(presenceDb*(0.42-0.16*shapeHighAmount));
        mbBrilliancePost=dbToLin(brillianceDb*(0.38-0.14*shapeHighAmount));
        mbLimiterForkCalibrationGain=dbToLin(-1.5-1.5*mbShape);
        const double densityShapeAmount=mbShape*0.55;
        std::array<double,6> compressorThresholdDb{};
        compressorThresholdDb[0]=baseThresholdDb[0]+(-14.2-baseThresholdDb[0])*densityShapeAmount;
        compressorThresholdDb[1]=baseThresholdDb[1]+(-14.2-baseThresholdDb[1])*densityShapeAmount;
        compressorThresholdDb[2]=baseThresholdDb[2]+(-14.2-baseThresholdDb[2])*densityShapeAmount;
        compressorThresholdDb[3]=baseThresholdDb[3]+(-14.2-baseThresholdDb[3])*densityShapeAmount-0.25*shapeHighAmount;
        compressorThresholdDb[4]=baseThresholdDb[4]-1.15*shapeHighAmount;
        compressorThresholdDb[5]=baseThresholdDb[5]-1.35*shapeHighAmount;
        b1Thresh=dbToLin(compressorThresholdDb[0]);b2Thresh=dbToLin(compressorThresholdDb[1]);b3Thresh=dbToLin(compressorThresholdDb[2]);b4Thresh=dbToLin(compressorThresholdDb[3]);b5Thresh=dbToLin(compressorThresholdDb[4]);b6Thresh=dbToLin(compressorThresholdDb[5]);
        presenceEdgeRecoveryGain=dbToLin(presenceDb*0.24*shapeHighAmount);
        presenceBodyRecoveryGain=dbToLin(presenceDb*0.42*shapeHighAmount);
        brillianceRecoveryGain=dbToLin(brillianceDb*0.50*shapeHighAmount);
    }else{
        b1Thresh=dbToLin(-9.5);b2Thresh=dbToLin(-11.5);b3Thresh=dbToLin(-13);b4Thresh=dbToLin(-14.5);b5Thresh=dbToLin(-16.5);b6Thresh=dbToLin(-18);
        mbPresencePost=mbBrilliancePost=mbLimiterForkCalibrationGain=presenceEdgeRecoveryGain=presenceBodyRecoveryGain=brillianceRecoveryGain=1.0;
    }
    mbEventAttack=std::exp(-1.0/(sampleRate*0.0040));
    mbEventMinimumRelease=std::exp(-1.0/std::max(1.0,sampleRate*0.004));
    mbEventMaximumRelease=std::exp(-1.0/std::max(1.0,sampleRate*0.060));
    const double shapeRecoveryAttack=1.0-std::exp(-1.0/(sampleRate*0.320));
    const double shapeRecoveryRelease=1.0-std::exp(-1.0/(sampleRate*0.070));
    shapeRecoveryAttackBlock=1.0-std::pow(1.0-shapeRecoveryAttack,16.0);
    shapeRecoveryReleaseBlock=1.0-std::pow(1.0-shapeRecoveryRelease,16.0);
    const double shapeServoLevel=1.0-std::exp(-1.0/(sampleRate*2.400));
    const double shapeServoGainCoefficient=1.0-std::exp(-1.0/(sampleRate*0.900));
    shapeServoLevelBlock=1.0-std::pow(1.0-shapeServoLevel,32.0);
    shapeServoGainBlock=1.0-std::pow(1.0-shapeServoGainCoefficient,32.0);
    constDb2LinMinus62=dbToLin(-6.2);constDb2LinMinus36=dbToLin(-3.6);clipRef=ceiling*.985;const double mbRef=ceiling*.985;mbWorkRef=mbRef/std::max(clipDriveMb*densityClipDrive,.25);b1DetScGain=densityDetectorGain*dbToLin(-bassEqDb*.55*bassScRelief-1.00*lowBassFloor);b2DetScGain=densityDetectorGain*dbToLin(-bassEqDb*.35*bassScRelief-.45*lowBassFloor);adaptBassSplitA=1-std::exp(-2*pi*190/sampleRate);adaptBassDetAttack=std::exp(-1/(sampleRate*.420));adaptBassDetRelease=std::exp(-1/(sampleRate*3.200));adaptBassGainUp=std::exp(-1/(sampleRate*1.150));adaptBassGainDown=std::exp(-1/(sampleRate*.130));adaptBassTargetLow=.33;adaptBassTargetHigh=.52;adaptBassMaxBoostDb=12*adaptiveBassCoupling;adaptBassMaxCutDb=7*adaptiveBassCoupling;
    foundationGuard.detAttack=std::exp(-1.0/(sampleRate*0.550));
    foundationGuard.detRelease=std::exp(-1.0/(sampleRate*3.000));
    foundationGuard.slowAttack=std::exp(-1.0/(sampleRate*4.500));
    foundationGuard.slowRelease=std::exp(-1.0/(sampleRate*10.000));
    foundationGuard.fastBoostAttackTick=std::exp(-16.0/(sampleRate*1.200));
    foundationGuard.fastBoostReleaseTick=std::exp(-16.0/(sampleRate*6.000));
    foundationGuard.fastCutAttackTick=std::exp(-16.0/(sampleRate*0.200));
    foundationGuard.fastCutReleaseTick=std::exp(-16.0/(sampleRate*6.000));
    foundationGuard.boostAttackTick=std::exp(-16.0/(sampleRate*1.000));
    foundationGuard.boostReleaseTick=std::exp(-16.0/(sampleRate*10.000));
    foundationGuard.boostSuppressTick=std::exp(-16.0/(sampleRate*0.080));
    foundationGuard.cutAttackTick=std::exp(-16.0/(sampleRate*0.250));
    foundationGuard.cutReleaseTick=std::exp(-16.0/(sampleRate*10.000));
    foundationGuard.cutSuppressTick=std::exp(-16.0/(sampleRate*1.200));
    foundationGuard.cutHoldoffSamples=static_cast<std::size_t>(std::floor(sampleRate*2.500+0.5));
    foundationGuard.voiceReturn=std::exp(-1.0/(sampleRate*2.200));
    foundationGuard.voiceWithdraw=std::exp(-1.0/(sampleRate*0.300));
    foundationGuard.feedbackAttackTick=std::exp(-16.0/(sampleRate*1.600));
    foundationGuard.feedbackReleaseTick=std::exp(-16.0/(sampleRate*4.000));
    foundationGuard.feedbackFastReleaseTick=std::exp(-16.0/(sampleRate*0.250));
    foundationGuard.feedbackBurdenAttackTick=std::exp(-16.0/(sampleRate*0.300));
    foundationGuard.feedbackBurdenReleaseTick=std::exp(-16.0/(sampleRate*1.200));
    foundationGuard.rumbleEnergyTick=std::exp(-16.0/(sampleRate*0.250));
    foundationGuard.rumbleAttackTick=std::exp(-16.0/(sampleRate*0.650));
    foundationGuard.rumbleReleaseTick=std::exp(-16.0/(sampleRate*2.000));
    foundationGuard.feedbackMaxAssistDb=12.0;
    foundationGuard.boostScale=adaptiveBassBoostCurve(adaptiveBassCoupling);
    foundationGuard.cutAuthority=adaptiveBassCutCurve(adaptiveBassCoupling);
    foundationGuard.link=clamp(lowCoherencePct*0.01,0.0,1.0);
    foundationGuard.withdrawAuthority=foundationGuard.cutAuthority;adaptTopDetAttack=std::exp(-1/(sampleRate*.360));adaptTopDetRelease=std::exp(-1/(sampleRate*2.800));adaptTopGainUp=std::exp(-1/(sampleRate*1.050));adaptTopGainDown=std::exp(-1/(sampleRate*.300));adaptTopEdgeTargetLow=.17;adaptTopEdgeTargetHigh=.40;adaptTopAirTargetLow=.030;adaptTopAirTargetHigh=.145;adaptTopPresenceMaxBoostDb=1.8*adaptiveTopCoupling;adaptTopPresenceMaxCutDb=3.8*adaptiveTopCoupling;adaptTopAirMaxBoostDb=3.6*adaptiveTopCoupling;adaptTopAirMaxCutDb=1.1*adaptiveTopCoupling;adaptTopAirHpA=1-std::exp(-2*pi*6800/sampleRate);bassClipSplitA=1-std::exp(-2*pi*145/sampleRate);bassClipSubhpA=1-std::exp(-2*pi*28/sampleRate);bassClipPreResA=1-std::exp(-2*pi*220/sampleRate);bassClipPreTh=ceiling*(.20-.10*bassClip);bassClipPreDrive=1+4.20*bassClip;bassClipPreAmt=std::min(1.0,bassClip*(.95+.15*bassClip));bassClipMakeup=1+.08*bassClip+.55*bassClip*bassClipDensity;recombClipThresh=ceiling*(.97-.16*recombControl);recombClipKnee=.68-.18*recombControl;if(coreMode==1&&finalStyleBlend>0.0000001){const double b=clamp(finalStyleBlend,0.0,1.0);clipStage1=clipRef*(.88+(.96-.88)*b);clipKnee1=.38+(.55-.38)*b;clipStage2=clipRef*(.975+(.998-.975)*b);clipKnee2=.24+(.35-.24)*b;}else if(clipperStyle==0){clipStage1=clipRef*.96;clipKnee1=.55;clipStage2=clipRef*.998;clipKnee2=.35;}else if(clipperStyle==1){clipStage1=clipRef*.92;clipKnee1=.46;clipStage2=clipRef*.990;clipKnee2=.30;}else if(clipperStyle==2){clipStage1=clipRef*.88;clipKnee1=.38;clipStage2=clipRef*.975;clipKnee2=.24;}else{clipStage1=clipRef*.80;clipKnee1=.26;clipStage2=clipRef*.950;clipKnee2=.18;}sideScale=stereoWidthPct*.01;widthMidFastAttack=std::exp(-1.0/(sampleRate*.0015));widthMidFastRelease=std::exp(-1.0/(sampleRate*.050));widthMidSlowAttack=std::exp(-1.0/(sampleRate*.030));widthMidSlowRelease=std::exp(-1.0/(sampleRate*.250));widthLevelAttack=std::exp(-1.0/(sampleRate*.008));widthLevelRelease=std::exp(-1.0/(sampleRate*.180));widthGainReduce=std::exp(-1.0/(sampleRate*.0005));widthGainRestore=std::exp(-1.0/(sampleRate*.035));deliveryCoeff={-1.3844169321618725e-20, -1.714921976246157e-05, -6.0455354465933198e-05, -0.00013469286395706965, -0.00023160238989120024, -0.00032332265730525061, -0.0003600104603619452, -0.00027504148634858571, 6.0606534200398679e-19, 0.00051085703445464983, 0.001250487575043453, 0.0021308196075711743, 0.0029665989652898936, 0.0034820444871444117, 0.0033483400339087972, 0.0022538484680090843, -3.5554623665915375e-18, -0.0033942098842589048, -0.0076047501191611674, -0.011962021412121901, -0.015484681728320933, -0.017004709450766174, -0.015382518566289935, -0.009787990225543379, 1.0995038784723119e-17, 0.013340886368729633, 0.028598727193283838, 0.043191291142155211, 0.053860575775541528, 0.057163886353818583, 0.050136702874308096, 0.031031400490199576, -2.2679691912594559e-17, -0.040425713396770119, -0.085190471768009743, -0.12699970260918969, -0.15705587807582772, -0.16618945163077609, -0.14624496557209393, -0.091517460508963533, 3.4139513012774583e-17, 0.12579016041624319, 0.27858892579190281, 0.44686041775752949, 0.61595203494645079, 0.76979541479457969, 0.89291964938217938, 0.97247963729367337, 0.99998818525633759, 0.97247963729367337, 0.89291964938217938, 0.76979541479457969, 0.61595203494645079, 0.44686041775752949, 0.27858892579190281, 0.12579016041624319, 3.4139513012774583e-17, -0.091517460508963533, -0.14624496557209393, -0.16618945163077609, -0.15705587807582772, -0.12699970260918969, -0.085190471768009743, -0.040425713396770119, -2.2679691912594559e-17, 0.031031400490199576, 0.050136702874308096, 0.057163886353818583, 0.053860575775541528, 0.043191291142155211, 0.028598727193283838, 0.013340886368729633, 1.0995038784723119e-17, -0.009787990225543379, -0.015382518566289935, -0.017004709450766174, -0.015484681728320933, -0.011962021412121901, -0.0076047501191611674, -0.0033942098842589048, -3.5554623665915375e-18, 0.0022538484680090843, 0.0033483400339087972, 0.0034820444871444117, 0.0029665989652898936, 0.0021308196075711743, 0.001250487575043453, 0.00051085703445464983, 6.0606534200398679e-19, -0.00027504148634858571, -0.0003600104603619452, -0.00032332265730525061, -0.00023160238989120024, -0.00013469286395706965, -6.0455354465933198e-05, -1.714921976246157e-05, -1.3844169321618725e-20, 0, 0, 0, 0, 0, 0, 0};bassPeakL.setPeak(65,1.4,bassEqDb,sampleRate);bassPeakR.setPeak(65,1.4,bassEqDb,sampleRate);foundationGuard.lp70L.setLowpass(70.0,0.70710678,sampleRate);foundationGuard.lp70R.setLowpass(70.0,0.70710678,sampleRate);
    foundationGuard.lp250L.setLowpass(250.0,0.70710678,sampleRate);foundationGuard.lp250R.setLowpass(250.0,0.70710678,sampleRate);
    foundationGuard.lp420L.setLowpass(420.0,0.70710678,sampleRate);foundationGuard.lp420R.setLowpass(420.0,0.70710678,sampleRate);
    foundationGuard.lp3700L.setLowpass(3700.0,0.70710678,sampleRate);foundationGuard.lp3700R.setLowpass(3700.0,0.70710678,sampleRate);
    foundationGuard.shelfL.setLowShelf(70.0,1.0,0.0,sampleRate);foundationGuard.shelfR.setLowShelf(70.0,1.0,0.0,sampleRate);
    foundationGuard.bodyL.setPeak(90.0,1.10,0.0,sampleRate);foundationGuard.bodyR.setPeak(90.0,1.10,0.0,sampleRate);transitionPeakL.setPeak(105,1.0,transitionFill*1.6,sampleRate);transitionPeakR.setPeak(105,1.0,transitionFill*1.6,sampleRate);lowFloorL.setPeak(58,.75,lowBassFloor*.65,sampleRate);lowFloorR.setPeak(58,.75,lowBassFloor*.65,sampleRate);if(topFilterMode==1){lpf15_1L.setLowpass(17000,.55,sampleRate);lpf15_1R.setLowpass(17000,.55,sampleRate);lpf15_2L.setLowpass(21000,.50,sampleRate);lpf15_2R.setLowpass(21000,.50,sampleRate);}else if(topFilterMode==2){lpf15_1L.setLowpass(15500,.58,sampleRate);lpf15_1R.setLowpass(15500,.58,sampleRate);lpf15_2L.setLowpass(15500,.58,sampleRate);lpf15_2R.setLowpass(15500,.58,sampleRate);}else{lpf15_1L.setLowpass(14500,.50,sampleRate);lpf15_1R.setLowpass(14500,.50,sampleRate);lpf15_2L.setLowpass(14500,.50,sampleRate);lpf15_2R.setLowpass(14500,.50,sampleRate);}lr4b1aL.setLowpass(150,.7071,sampleRate);lr4b1aR.setLowpass(150,.7071,sampleRate);lr4b1bL.setLowpass(150,.7071,sampleRate);lr4b1bR.setLowpass(150,.7071,sampleRate);lr4b2aL.setLowpass(420,.7071,sampleRate);lr4b2aR.setLowpass(420,.7071,sampleRate);lr4b2bL.setLowpass(420,.7071,sampleRate);lr4b2bR.setLowpass(420,.7071,sampleRate);lr4b3aL.setLowpass(700,.7071,sampleRate);lr4b3aR.setLowpass(700,.7071,sampleRate);lr4b3bL.setLowpass(700,.7071,sampleRate);lr4b3bR.setLowpass(700,.7071,sampleRate);lr4b4aL.setLowpass(1600,.7071,sampleRate);lr4b4aR.setLowpass(1600,.7071,sampleRate);lr4b4bL.setLowpass(1600,.7071,sampleRate);lr4b4bR.setLowpass(1600,.7071,sampleRate);lr4b5aL.setLowpass(3700,.7071,sampleRate);lr4b5aR.setLowpass(3700,.7071,sampleRate);lr4b5bL.setLowpass(3700,.7071,sampleRate);lr4b5bR.setLowpass(3700,.7071,sampleRate);fcsResidueA=1-std::exp(-2*pi*12000/sampleRate);
}


double OptiLabCore::adaptiveStereoWidthGain(double midDet,double sideDet,double extraRequest){
    widthMidFast = midDet>widthMidFast ? midDet+widthMidFastAttack*(widthMidFast-midDet) : midDet+widthMidFastRelease*(widthMidFast-midDet);
    widthMidSlow = midDet>widthMidSlow ? midDet+widthMidSlowAttack*(widthMidSlow-midDet) : midDet+widthMidSlowRelease*(widthMidSlow-midDet);
    widthMidEnv = midDet>widthMidEnv ? midDet+widthLevelAttack*(widthMidEnv-midDet) : midDet+widthLevelRelease*(widthMidEnv-midDet);
    widthSideEnv = sideDet>widthSideEnv ? sideDet+widthLevelAttack*(widthSideEnv-sideDet) : sideDet+widthLevelRelease*(widthSideEnv-sideDet);
    const double ratio=widthSideEnv/std::max(widthMidEnv,tiny);
    const double transient=clamp((widthMidFast/std::max(widthMidSlow,tiny)-1.0)*1.5,0.0,1.0);
    const double sideGate=clamp((ratio-.012)*20.8333333333333,0.0,1.0);
    const double levelGate=clamp((widthMidEnv-.001)*111.111111111111,0.0,1.0);
    const double narrowness=clamp((.45-ratio)*2.85714285714286,0.0,1.0);
    const double character=clamp(.35+.40*transient+.25*narrowness,0.0,1.0);
    const double ratioCap=ratio>tiny?clamp((.92/ratio-1.0)/std::max(extraRequest,tiny),0.0,1.0):1.0;
    const double target=sideGate*levelGate*character*ratioCap;
    widthAdaptiveGain=target<widthAdaptiveGain ? target+widthGainReduce*(widthAdaptiveGain-target) : target+widthGainRestore*(widthAdaptiveGain-target);
    widthAdaptiveGain=std::min(widthAdaptiveGain,ratioCap);
    return widthAdaptiveGain;
}


void OptiLabCore::processHybrid(double& l,double& r){
    if(hybridTotalDelaySamples<=0) return;
    const int w=hybridWrite;
    hybridRawL[(std::size_t)w]=l;hybridRawR[(std::size_t)w]=r;
    const double thresholdDrive=std::max(finalThresholdDriveS,1.0);
    const double workLimit=ceiling/thresholdDrive;
    hybridWorkLimit[(std::size_t)w]=workLimit;hybridMakeup[(std::size_t)w]=thresholdDrive;
    hybridEventGate[(std::size_t)w]=0.0;
    int outRead=w-hybridTotalDelaySamples;if(outRead<0)outRead+=hybridHistoryLength;
    if(hybridMix<=0.0000001){hybridLimiterWindowTracked=false;l=hybridRawL[(std::size_t)outRead];r=hybridRawR[(std::size_t)outRead];hybridWrite=(hybridWrite+1)%hybridHistoryLength;++hybridSampleClock;return;}
    constexpr double depthDb=6.0,guardStart=-20.0,guardFull=-16.0,shortZero=.45,shortFull=.60,longFull=1.50,longZero=2.00,tonalVeto=.970;
    const double candL=hybridShaveToLimit(l,workLimit,depthDb),candR=hybridShaveToLimit(r,workLimit,depthDb);hybridCandidateL[(std::size_t)w]=candL;hybridCandidateR[(std::size_t)w]=candR;const double ddL=candL-l,ddR=candR-r;
    hybridRefEnergySum-=hybridRefEnergy[(std::size_t)hybridEnergyWrite];hybridDeltaEnergySum-=hybridDeltaEnergy[(std::size_t)hybridEnergyWrite];const double re=l*l+r*r,de=ddL*ddL+ddR*ddR;hybridRefEnergy[(std::size_t)hybridEnergyWrite]=re;hybridDeltaEnergy[(std::size_t)hybridEnergyWrite]=de;hybridRefEnergySum+=re;hybridDeltaEnergySum+=de;hybridEnergyWrite=(hybridEnergyWrite+1)%hybridBurdenWindowSamples;hybridEnergyCount=std::min(hybridEnergyCount+1,hybridBurdenWindowSamples);
    const double refRms=std::sqrt(std::max(hybridRefEnergySum,0.0)/std::max(2.0*(double)hybridEnergyCount,1.0));double burdenTarget=1.0;if(refRms>=dbToLin(-60)){const double ratio=std::max(hybridDeltaEnergySum,0.0)/std::max(hybridRefEnergySum,1e-18),db=ratio>1e-12?4.342944819032518*std::log(ratio):-120.0;if(db>=guardFull)burdenTarget=0;else if(db>guardStart)burdenTarget=1-smoothstep01((db-guardStart)/(guardFull-guardStart));}hybridBurdenAccept=burdenTarget<hybridBurdenAccept?burdenTarget+hybridBurdenAttack*(hybridBurdenAccept-burdenTarget):burdenTarget+hybridBurdenRelease*(hybridBurdenAccept-burdenTarget);hybridBurdenAccept=clamp(hybridBurdenAccept,0,1);hybridBurden[(std::size_t)w]=hybridBurdenAccept;
    const double removed=absmax2(ddL,ddR);const bool active=removed>workLimit*.001,newEvent=active&&!hybridCandidateActivePrev,endEvent=!active&&hybridCandidateActivePrev;if(newEvent){hybridEventStartAbs=hybridSampleClock;hybridEventStartRing=w;hybridEventCorrelation=hybridEventTonalCorrelation(hybridSampleClock);hybridOnset3=hybridOnset2;hybridOnset2=hybridOnset1;hybridOnset1=hybridSampleClock;}if(endEvent&&hybridEventStartAbs>=0){const auto dur64=hybridSampleClock-hybridEventStartAbs;const int dur=(int)std::min<std::int64_t>(dur64,hybridHistoryLength-1);const double ms=(double)dur64*1000.0/sampleRate,low=smoothstep01((ms-shortZero)/(shortFull-shortZero)),high=1-smoothstep01((ms-longFull)/(longZero-longFull)),tonal=hybridEventCorrelation>=tonalVeto?0.0:1.0;double accept=low*high*tonal;if(dur64>hybridClassificationSamples)accept=0;int fill=hybridEventStartRing;for(int i=0;i<dur;++i){hybridEventGate[(std::size_t)fill]=accept;fill=(fill+1)%hybridHistoryLength;}hybridEventStartAbs=-1;}hybridCandidateActivePrev=active;
    int cr=w-hybridClassificationSamples;if(cr<0)cr+=hybridHistoryLength;const double rawL=hybridRawL[(std::size_t)cr],rawR=hybridRawR[(std::size_t)cr],accept=clamp(std::min(hybridBurden[(std::size_t)cr],hybridEventGate[(std::size_t)cr]),0,1),shL=rawL+(hybridCandidateL[(std::size_t)cr]-rawL)*accept,shR=rawR+(hybridCandidateR[(std::size_t)cr]-rawR)*accept;hybridShavedL[(std::size_t)cr]=shL;hybridShavedR[(std::size_t)cr]=shR;const double classifiedLimit=hybridWorkLimit[(std::size_t)cr],det=absmax2(shL,shR),required=det>classifiedLimit?classifiedLimit/std::max(det,tiny):1.0;hybridRequiredGain[(std::size_t)cr]=required;hybridRequiredActive[(std::size_t)cr]=required<1.0?1:0;
    if(!hybridLimiterWindowTracked){hybridLimiterActiveCount=0;for(int d=0;d<=hybridLimiterLookaheadSamples;++d){int ii=outRead+d;if(ii>=hybridHistoryLength)ii-=hybridHistoryLength;hybridLimiterActiveCount+=hybridRequiredActive[(std::size_t)ii]?1:0;}hybridLimiterWindowTracked=true;}else{int leaving=outRead-1;if(leaving<0)leaving+=hybridHistoryLength;if(hybridRequiredActive[(std::size_t)leaving])--hybridLimiterActiveCount;if(hybridRequiredActive[(std::size_t)cr])++hybridLimiterActiveCount;}
    double tg=1.0;if(hybridLimiterLookaheadSamples>0&&hybridLimiterActiveCount>0){for(int d=0;d<=hybridLimiterLookaheadSamples;++d){int ii=outRead+d;if(ii>=hybridHistoryLength)ii-=hybridHistoryLength;const double req=hybridRequiredGain[(std::size_t)ii],shape=hybridAttackShape[(std::size_t)d];tg=std::min(tg,req+(1-req)*shape);}}else if(hybridLimiterLookaheadSamples<=0)tg=hybridRequiredGain[(std::size_t)outRead];hybridLimiterGain=tg<hybridLimiterGain?tg:tg+hybridLimiterRelease*(hybridLimiterGain-tg);if(hybridLimiterGain>.999999999)hybridLimiterGain=1;
    const double rawOutL=hybridRawL[(std::size_t)outRead],rawOutR=hybridRawR[(std::size_t)outRead];double procL=hybridShavedL[(std::size_t)outRead]*hybridLimiterGain*hybridMakeup[(std::size_t)outRead],procR=hybridShavedR[(std::size_t)outRead]*hybridLimiterGain*hybridMakeup[(std::size_t)outRead];procL=hardLimit(procL,ceiling);procR=hardLimit(procR,ceiling);l=hardLimit(rawOutL+(procL-rawOutL)*hybridMix,ceiling);r=hardLimit(rawOutR+(procR-rawOutR)*hybridMix,ceiling);hybridWrite=(hybridWrite+1)%hybridHistoryLength;++hybridSampleClock;
}


void OptiLabCore::processDelivery(double& l,double& r){
    const int w=deliveryWrite;
    deliveryBufL[(std::size_t)w]=l;
    deliveryBufR[(std::size_t)w]=r;
    deliveryRequired[(std::size_t)w]=1.0;
    for(int t=deliveryDetectorTaps-1;t>0;--t){
        deliveryHistL[(std::size_t)t]=deliveryHistL[(std::size_t)(t-1)];
        deliveryHistR[(std::size_t)t]=deliveryHistR[(std::size_t)(t-1)];
    }
    deliveryHistL[0]=l;
    deliveryHistR[0]=r;
    double peak=absmax2(l,r);
    for(int phase=0;phase<deliveryDetectorPhases;++phase){
        double sumL=0.0,sumR=0.0;
        for(int tap=0;tap<deliveryDetectorTaps;++tap){
            const double coeff=deliveryCoeff[(std::size_t)(tap*deliveryDetectorPhases+phase)];
            sumL+=deliveryHistL[(std::size_t)tap]*coeff;
            sumR+=deliveryHistR[(std::size_t)tap]*coeff;
        }
        peak=std::max(peak,absmax2(sumL,sumR));
    }
    const double required=peak>deliveryTarget?deliveryTarget/std::max(peak,1.0e-12):1.0;
    int detectorIndex=w-deliveryDetectorDelaySamples;if(detectorIndex<0)detectorIndex+=deliveryBufferLength;
    deliveryRequired[(std::size_t)detectorIndex]=std::min(deliveryRequired[(std::size_t)detectorIndex],required);
    int read=w-deliveryLookaheadSamples;if(read<0)read+=deliveryBufferLength;
    double targetGain=1.0;
    for(int ahead=0;ahead<=deliveryAnticipationSamples;++ahead){
        int index=read+ahead;if(index>=deliveryBufferLength)index-=deliveryBufferLength;
        const double request=deliveryRequired[(std::size_t)index];
        const double u=static_cast<double>(ahead)/static_cast<double>(deliveryAnticipationSamples);
        const double shape=u*u*(3.0-2.0*u);
        targetGain=std::min(targetGain,request+(1.0-request)*shape);
    }
    deliveryGain=targetGain<deliveryGain?targetGain:targetGain+deliveryRelease*(deliveryGain-targetGain);
    if(deliveryGain>.999999999)deliveryGain=1.0;
    l=deliveryBufL[(std::size_t)read]*deliveryGain;
    r=deliveryBufR[(std::size_t)read]*deliveryGain;
    if(++finalLoadCounter>=64){
        finalLoadCounter=0;
        const double finalLevelFactor=clamp((finalFullEnv.e-ceiling*.55)/std::max(ceiling*.35,tiny),0.0,1.0);
        const double finalDynamicGain=peakOnlyFinalLimiter?1.0:dbToLin(-2.0*clipRestraint*finalLevelFactor);
        const double finalPreGain=1.0-prelimitMix*(1.0-preclip.gain);
        const double finalHybridGain=1.0-hybridMix*(1.0-hybridLimiterGain);
        const double finalLoadGain=clamp(finalThresholdGuardGain*finalDynamicGain*finalPreGain*finalHybridGain*deliveryGain,tiny,1.0);
        if(activityTracking)currentFinalGain=finalLoadGain;
        const double liftTarget=(gateState<.50&&startupActivity>=gateLin)?streamAgcLiftDb:agcLiftStateDb;
        const double liftCoefficient=liftTarget>agcLiftStateDb?agcLiftAttackBlock:agcLiftReleaseBlock;
        agcLiftStateDb=liftTarget+liftCoefficient*(agcLiftStateDb-liftTarget);
        const double loadDb=std::max(0.0,-linToDb(finalLoadGain));
        const double backoffTarget=clamp((loadDb-.60)*.80,0.0,2.0)*finalBackoffMix;
        const double backoffCoefficient=backoffTarget>finalBackoffDb?finalBackoffAttackBlock:finalBackoffReleaseBlock;
        finalBackoffDb=backoffTarget+backoffCoefficient*(finalBackoffDb-backoffTarget);
        finalFoundationBurden=clamp(finalBackoffDb/.60,0.0,1.0);
        finalThresholdDriveTarget=dbToLin(-std::min(0.0,finalThresholdDb+.90*finalBackoffDb));
        agcTarget=dbToLin(agcTargetBaseDb+agcLiftStateDb-.35*finalBackoffDb);
    }
    deliveryRequired[(std::size_t)read]=1.0;
    deliveryWrite=(deliveryWrite+1)%deliveryBufferLength;
}

std::pair<float,float> OptiLabCore::processSample(float left,float right){
    double l=std::isfinite(left)?static_cast<double>(left):0.0,r=std::isfinite(right)?static_cast<double>(right):0.0;l=std::abs(l)<1e12?l:0;r=std::abs(r)<1e12?r:0;const double inputRawL=l,inputRawR=r;l*=inputGain;r*=inputGain;if(params.mode==Mode::StreamPolish){const double streamInputL=l,streamInputR=r;const double hpl=hp30L.hp(streamInputL,hpf30A),hpr=hp30R.hp(streamInputR,hpf30A);const double rejectedL=streamInputL-hpl,rejectedR=streamInputR-hpr;foundationGuard.rumbleSubAccum+=(rejectedL*rejectedL+rejectedR*rejectedR)*0.5;foundationGuard.rumbleTotalAccum+=(streamInputL*streamInputL+streamInputR*streamInputR)*0.5;++foundationGuard.rumbleCount;l=streamInputL+(hpl-streamInputL)*streamHpfMix;r=streamInputR+(hpr-streamInputR)*streamHpfMix;}else if(subsonicHpf){l=hp30L.hp(l,hpf30A);r=hp30R.hp(r,hpf30A);}if(phaseStages>0){for(int i=0;i<phaseStages;++i){l=apL[i].run(l,apC[i]);r=apR[i].run(r,apC[i]);}}
    startupActivity=std::max(absmax2(l,r),startupActivity*startupActivityRelease);const double agcL=l*agcDrive,agcR=r*agcDrive;const double lowL=crossoverModel==1?agcLpL.lp2(agcL,agcSplitA):agcLpL.lp(agcL,agcSplitA),lowR=crossoverModel==1?agcLpR.lp2(agcR,agcSplitA):agcLpR.lp(agcR,agcSplitA),highL=agcL-lowL,highR=agcR-lowR,lowDet=absmax2(lowL,lowR),highDet=absmax2(highL,highR),fullDet=absmax2(agcL,agcR);double lowEnv=agcLowEnv.run(lowDet,agcEnvAttack,agcRelease),highEnv=agcHighEnv.run(highDet,agcEnvAttack,agcRelease);gateProgEnv=std::max(fullDet,gateProgEnv*gateDetectorRelease);const double gateOpenNow=fullDet>=gateLin?1.0:0.0,gateTarget=gateProgEnv<gateLin?1.0:0.0,gatePrevState=gateState;gateClosedMemory=std::max(gateClosedMemory*gateReopenDecay,gateState);if(gateOpenNow>0)gateState*=gateOpenCoeff;else if(gateTarget>gateState)gateState=gateTarget+gateCloseCoeff*(gateState-gateTarget);else gateState=gateTarget+gateOpenCoeff*(gateState-gateTarget);gateState=clamp(gateState,0,1);const double gateEffective=gateState*(1-gateOpenNow);gateReopenPulse=gateOpenNow*clamp(std::max(gatePrevState,gateClosedMemory)*gateReopenPulseScale,0,1);gateReopenEnv=std::max(gateReopenEnv*gateReopenDecay,gateReopenPulse);if(gateOpenNow>0)gateClosedMemory*=gateReopenDecay;if(gateReopenEnv>0){const double clearCoeff=1-gateReopenEnv*(1-gateReopenEnvRelease);lowEnv=agcLowEnv.set(lowDet+clearCoeff*(lowEnv-lowDet));highEnv=agcHighEnv.set(highDet+clearCoeff*(highEnv-highDet));}double lowTargetGain=clamp(agcTarget/std::max(lowEnv,tiny),agcMinGain,agcMaxGain),highTargetGain=clamp(agcTarget/std::max(highEnv,tiny),agcMinGain,agcMaxGain);lowTargetGain=lowTargetGain*(1-bassCoupling)+highTargetGain*bassCoupling;if(gateEffective>0){lowTargetGain=lowTargetGain*(1-gateEffective)+std::min(lowTargetGain,agcLGain)*gateEffective;highTargetGain=highTargetGain*(1-gateEffective)+std::min(highTargetGain,agcHGain)*gateEffective;}const double pdAgc=pdRelease*.15,agcLowDepth=clamp((1-agcLGain)/.75,0,1),agcHighDepth=clamp((1-agcHGain)/.75,0,1);double agcLowRel=agcRelease*(1-pdAgc*agcLowDepth)+agcReleaseSlow*(pdAgc*agcLowDepth),agcHighRel=agcRelease*(1-pdAgc*agcHighDepth)+agcReleaseSlow*(pdAgc*agcHighDepth);agcLowRel=agcLowRel*(1-gateEffective)+gateAgcFreezeRelease*gateEffective;agcHighRel=agcHighRel*(1-gateEffective)+gateAgcFreezeRelease*gateEffective;const double gateReopenRelMix=gateReopenEnv*(.35+.45*gateReopenStrength),agcGateReopenRelMix=gateReopenEnv*(.06+.16*gateReopenStrength);agcLowRel=agcLowRel*(1-agcGateReopenRelMix)+gateReopenRelease*agcGateReopenRelMix;agcHighRel=agcHighRel*(1-agcGateReopenRelMix)+gateReopenRelease*agcGateReopenRelMix;agcLGain=lowTargetGain<agcLGain?lowTargetGain+agcGainAttack*(agcLGain-lowTargetGain):lowTargetGain+agcLowRel*(agcLGain-lowTargetGain);agcHGain=highTargetGain<agcHGain?highTargetGain+agcGainAttack*(agcHGain-highTargetGain):highTargetGain+agcHighRel*(agcHGain-highTargetGain);const double driftAmt=(1-gateAgcDriftCoeff)*gateEffective;agcLGain+=driftAmt*(gateAgcDriftTarget-agcLGain);agcHGain+=driftAmt*(gateAgcDriftTarget-agcHGain);const double agcDriveSafe=std::max(agcDrive,tiny),agcLowProcGain=agcDrive*agcLGain,agcHighProcGain=agcDrive*agcHGain,agcLowAuthority=agcLowProcGain<1?agcDownMix:agcMix,agcHighAuthority=agcHighProcGain<1?agcDownMix:agcMix,agcLowEffGain=1+(agcLowProcGain-1)*agcLowAuthority,agcHighEffGain=1+(agcHighProcGain-1)*agcHighAuthority;if(activityTracking){currentAgcLowEffGain=agcLowEffGain;currentAgcHighEffGain=agcHighEffGain;}l=(lowL/agcDriveSafe)*agcLowEffGain+(highL/agcDriveSafe)*agcHighEffGain;r=(lowR/agcDriveSafe)*agcLowEffGain+(highR/agcDriveSafe)*agcHighEffGain;if(postAgcSmoothDriveAmt>.0000001){l=postAgcRoundL.run(l,postAgcSmoothDriveAmt)*postAgcSmoothRecoveryGain;r=postAgcRoundR.run(r,postAgcSmoothDriveAmt)*postAgcSmoothRecoveryGain;}
    if(masteringLookaheadSamples>0){const double masterSideDet=absmax2(l,r),masterRawDet=absmax2(inputRawL,inputRawR),masterAmpDet=masterSideDet;const bool active=std::max(masterSideDet,masterRawDet)>masterStartupActiveThresh;if(masterStartupArmed>0){if(active){if(masterStartupAge<masterStartupPrimeWindow){masterBufL.fill(l);masterBufR.fill(r);masterWrite=0;masterRawEnv.set(std::max(masterRawDet,tiny));masterAmpEnv.set(std::max(masterAmpDet,tiny));masterCatchEnv.set(std::max(masterSideDet,tiny));masterCatchGain=1;}masterStartupArmed=0;}else{++masterStartupAge;if(masterStartupAge>=masterStartupPrimeWindow)masterStartupArmed=0;}}const double rawLevel=masterRawEnv.run(masterRawDet,masterEnvAttack,masterEnvRelease),ampLevel=masterAmpEnv.run(masterAmpDet,masterEnvAttack,masterEnvRelease),netMakeupDb=linToDb(ampLevel/std::max(rawLevel,tiny)),allow=clamp((netMakeupDb-3.0)/9.0,0,1),catchDet=masterCatchEnv.run(masterSideDet,masterCatchAttack,masterCatchRelease);double targetGain=catchDet>constDb2LinMinus62?constDb2LinMinus62/std::max(catchDet,tiny):1;targetGain=clamp(targetGain,constDb2LinMinus36,1);targetGain=1-allow*(1-targetGain);masterCatchGain=targetGain<masterCatchGain?targetGain+masterCatchAttack*(masterCatchGain-targetGain):targetGain+masterCatchRelease*(masterCatchGain-targetGain);int read=masterWrite-masteringLookaheadSamples;if(read<0)read+=masterBufferLength;const double delayedL=masterBufL[read],delayedR=masterBufR[read];masterBufL[masterWrite]=l;masterBufR[masterWrite]=r;masterWrite=(masterWrite+1)%masterBufferLength;l=delayedL*masterCatchGain;r=delayedR*masterCatchGain;}else{masterCatchGain=1;masterStartupArmed=1;masterStartupAge=0;}
    const double bassPreL=l,bassPreR=r;
    const double bassBoostedL=bassPeakL.run(l),bassBoostedR=bassPeakR.run(r);
    double legacyBassL=bassBoostedL,legacyBassR=bassBoostedR;
    if(foundationMix<0.9999999&&adaptiveBassCoupling>0){const double abLowL=adaptBassLpL.lp2(bassBoostedL,adaptBassSplitA),abLowR=adaptBassLpR.lp2(bassBoostedR,adaptBassSplitA),abHighL=bassBoostedL-abLowL,abHighR=bassBoostedR-abLowR,bassDet=absmax2(abLowL,abLowR),progDet=std::max(absmax2(bassBoostedL,bassBoostedR),absmax2(abHighL,abHighR)*1.20),bassEnv=adaptBassEnv.run(bassDet,adaptBassDetAttack,adaptBassDetRelease),progEnv=adaptProgEnv.run(progDet,adaptBassDetAttack,adaptBassDetRelease),ratio=bassEnv/std::max(progEnv,tiny),thin=clamp((adaptBassTargetLow-ratio)/std::max(adaptBassTargetLow-.105,tiny),0,1),heavy=clamp((ratio-adaptBassTargetHigh)/std::max(.82-adaptBassTargetHigh,tiny),0,1),gainTarget=dbToLin(adaptBassMaxBoostDb*thin-adaptBassMaxCutDb*heavy);if(adaptBassGain<=0)adaptBassGain=1;adaptBassGain=gainTarget<adaptBassGain?gainTarget+adaptBassGainDown*(adaptBassGain-gainTarget):gainTarget+adaptBassGainUp*(adaptBassGain-gainTarget);legacyBassL=abHighL+abLowL*adaptBassGain;legacyBassR=abHighR+abLowR*adaptBassGain;}
    if(foundationMix>0.0000001){const auto fg=processFoundationGuard(bassPreL,bassPreR,bassBoostedL,bassBoostedR);l=legacyBassL+(fg.first-legacyBassL)*foundationMix;r=legacyBassR+(fg.second-legacyBassR)*foundationMix;}else{l=legacyBassL;r=legacyBassR;}
    if(bassClip>0){const double lowL2=bassclipSplitL.lp2(l,bassClipSplitA),lowR2=bassclipSplitR.lp2(r,bassClipSplitA),highL2=l-lowL2,highR2=r-lowR2,driveL=bassclipHpfL.hp(lowL2,bassClipSubhpA),driveR=bassclipHpfR.hp(lowR2,bassClipSubhpA);l=highL2+(lowL2-driveL)+bassclipPreL.run(driveL,bassClipPreTh,bassClipPreAmt,.42,bassClipPreDrive,.22,bassClipPreResA)*bassClipMakeup;r=highR2+(lowR2-driveR)+bassclipPreR.run(driveR,bassClipPreTh,bassClipPreAmt,.42,bassClipPreDrive,.22,bassClipPreResA)*bassClipMakeup;}
    l*=densityAudioGain;r*=densityAudioGain;double b1L,b2L,b3L,b4L,b5L,b6L,b1R,b2R,b3R,b4R,b5R,b6R;if(crossoverModel==3){const double lp1L=lr4b1bL.run(lr4b1aL.run(l)),lp2L=lr4b2bL.run(lr4b2aL.run(l)),lp3L=lr4b3bL.run(lr4b3aL.run(l)),lp4L=lr4b4bL.run(lr4b4aL.run(l)),lp5L=lr4b5bL.run(lr4b5aL.run(l));b1L=lp1L;b2L=lp2L-lp1L;b3L=lp3L-lp2L;b4L=lp4L-lp3L;b5L=lp5L-lp4L;b6L=l-lp5L;const double lp1R=lr4b1bR.run(lr4b1aR.run(r)),lp2R=lr4b2bR.run(lr4b2aR.run(r)),lp3R=lr4b3bR.run(lr4b3aR.run(r)),lp4R=lr4b4bR.run(lr4b4aR.run(r)),lp5R=lr4b5bR.run(lr4b5aR.run(r));b1R=lp1R;b2R=lp2R-lp1R;b3R=lp3R-lp2R;b4R=lp4R-lp3R;b5R=lp5R-lp4R;b6R=r-lp5R;}else{const double lp1L=xbL[0].lp2(l,x1A),lp2L=xbL[1].lp2(l,x2A),lp3L=xbL[2].lp2(l,x3A),lp4L=xbL[3].lp2(l,x4A),lp5L=xbL[4].lp2(l,x5A);b1L=lp1L;b2L=lp2L-lp1L;b3L=lp3L-lp2L;b4L=lp4L-lp3L;b5L=lp5L-lp4L;b6L=l-lp5L;const double lp1R=xbR[0].lp2(r,x1A),lp2R=xbR[1].lp2(r,x2A),lp3R=xbR[2].lp2(r,x3A),lp4R=xbR[3].lp2(r,x4A),lp5R=xbR[4].lp2(r,x5A);b1R=lp1R;b2R=lp2R-lp1R;b3R=lp3R-lp2R;b4R=lp4R-lp3R;b5R=lp5R-lp4R;b6R=r-lp5R;}
    double topPresenceAdaptGain=1,topAirAdaptGain=1;if(adaptiveTopCoupling>0){const double b4Det=absmax2(b4L,b4R),b5Det=absmax2(b5L,b5R),b6Det=absmax2(b6L,b6R),airL=adaptTopAirHpL.hp(l,adaptTopAirHpA),airR=adaptTopAirHpR.hp(r,adaptTopAirHpA),airDet=absmax2(airL,airR),edgeDet=b4Det*.30+b5Det*.85+b6Det*.18,progDet=std::max(absmax2(l,r),std::max(edgeDet,airDet)*1.08),edgeRatio=adaptTopEdgeEnv.run(edgeDet,adaptTopDetAttack,adaptTopDetRelease)/std::max(adaptTopEdgeProgEnv.run(progDet,adaptTopDetAttack,adaptTopDetRelease),tiny),airRatio=adaptTopAirEnv.run(airDet,adaptTopDetAttack,adaptTopDetRelease)/std::max(adaptTopAirProgEnv.run(progDet,adaptTopDetAttack,adaptTopDetRelease),tiny),edgeDull=clamp((adaptTopEdgeTargetLow-edgeRatio)/std::max(adaptTopEdgeTargetLow-.060,tiny),0,1),edgeBright=clamp((edgeRatio-adaptTopEdgeTargetHigh)/std::max(.78-adaptTopEdgeTargetHigh,tiny),0,1);double presenceTargetDb=adaptTopPresenceMaxBoostDb*edgeDull-adaptTopPresenceMaxCutDb*edgeBright;const double airDull=clamp((adaptTopAirTargetLow-airRatio)/std::max(adaptTopAirTargetLow-.006,tiny),0,1),airBright=clamp((airRatio-adaptTopAirTargetHigh)/std::max(.38-adaptTopAirTargetHigh,tiny),0,1);double airTargetDb=adaptTopAirMaxBoostDb*airDull-adaptTopAirMaxCutDb*airBright;const double edgeGuard=clamp((edgeRatio-.46)/.34,0,1);airTargetDb-=std::max(airTargetDb,0.0)*(.55*edgeGuard);const double presenceTarget=dbToLin(presenceTargetDb),airTarget=dbToLin(airTargetDb);if(adaptTopPresenceGain<=0)adaptTopPresenceGain=1;adaptTopPresenceGain=presenceTarget<adaptTopPresenceGain?presenceTarget+adaptTopGainDown*(adaptTopPresenceGain-presenceTarget):presenceTarget+adaptTopGainUp*(adaptTopPresenceGain-presenceTarget);if(adaptTopAirGain<=0)adaptTopAirGain=1;adaptTopAirGain=airTarget<adaptTopAirGain?airTarget+adaptTopGainDown*(adaptTopAirGain-airTarget):airTarget+adaptTopGainUp*(adaptTopAirGain-airTarget);topPresenceAdaptGain=adaptTopPresenceGain;topAirAdaptGain=adaptTopAirGain;}else adaptTopPresenceGain=adaptTopAirGain=1;b4L*=presenceGain*topPresenceAdaptGain;b4R*=presenceGain*topPresenceAdaptGain;b5L*=presenceGain*topPresenceAdaptGain;b5R*=presenceGain*topPresenceAdaptGain;b6L*=brillianceGain*topAirAdaptGain;b6R*=brillianceGain*topAirAdaptGain;
    if(foundationMix>0.0000001){foundationGuard.feedbackB1Accum+=(b1L*b1L+b1R*b1R)*0.5;foundationGuard.feedbackB2Accum+=(b2L*b2L+b2R*b2R)*0.5;++foundationGuard.feedbackCount;}
    const double gateXt2Strength=gateEffective*.78;double lowBandReleaseGated=lowBandRelease*(1-gateXt2Strength)+gateXt2FreezeRelease*gateXt2Strength,lowBandReleaseSlowGated=lowBandReleaseSlow*(1-gateXt2Strength)+gateXt2FreezeRelease*gateXt2Strength,bandReleaseGated=bandRelease*(1-gateXt2Strength)+gateXt2FreezeRelease*gateXt2Strength,bandReleaseSlowGated=bandReleaseSlow*(1-gateXt2Strength)+gateXt2FreezeRelease*gateXt2Strength;lowBandReleaseGated=lowBandReleaseGated*(1-gateReopenRelMix)+gateReopenRelease*gateReopenRelMix;lowBandReleaseSlowGated=lowBandReleaseSlowGated*(1-gateReopenRelMix)+gateReopenRelease*gateReopenRelMix;bandReleaseGated=bandReleaseGated*(1-gateReopenRelMix)+gateReopenRelease*gateReopenRelMix;bandReleaseSlowGated=bandReleaseSlowGated*(1-gateReopenRelMix)+gateReopenRelease*gateReopenRelMix;std::array<double,6> sourceL{b1L,b2L,b3L,b4L,b5L,b6L},sourceR{b1R,b2R,b3R,b4R,b5R,b6R};
    std::array<double,6> compGain{};
    compGain[0]=lim[0].bandLimitPd(absmax2(sourceL[0],sourceR[0])*b1DetScGain,b1Thresh,bandAttack,lowBandReleaseGated,lowBandReleaseSlowGated,pdRelease);
    compGain[1]=lim[1].bandLimitPd(absmax2(sourceL[1],sourceR[1])*b2DetScGain,b2Thresh,bandAttack,lowBandReleaseGated,lowBandReleaseSlowGated,pdRelease);
    compGain[2]=lim[2].bandLimitPdSoft(absmax2(sourceL[2],sourceR[2])*densityDetectorGain,b3Thresh,upperMidBandAttack,bandReleaseGated,bandReleaseSlowGated,pdRelease,4.2,.30,.14);
    compGain[3]=lim[3].bandLimitPdSoft(absmax2(sourceL[3],sourceR[3])*densityDetectorGain,b4Thresh,upperBandAttack,bandReleaseGated,bandReleaseSlowGated,pdRelease,3.1,.42,.16);
    compGain[4]=lim[4].bandLimitPdSoft(absmax2(sourceL[4],sourceR[4])*densityDetectorGain,b5Thresh,upperBandAttack,bandReleaseGated,bandReleaseSlowGated,pdRelease,2.6,.55,.18);
    compGain[5]=lim[5].bandLimitPdSoft(absmax2(sourceL[5],sourceR[5])*densityDetectorGain,b6Thresh,upperBandAttack,bandReleaseGated,bandReleaseSlowGated,pdRelease,2.4,.65,.20);
    for(double&g:compGain)g=1.0-xt2Mix*(1.0-g);
    const double compLowSharedGain=std::sqrt(std::max(compGain[0]*compGain[1],tiny));
    compGain[0]=compGain[0]*(1.0-lowCoherence)+compLowSharedGain*lowCoherence;
    compGain[1]=compGain[1]*(1.0-lowCoherence)+compLowSharedGain*lowCoherence;
    const double band6ControlledGain=std::min(compGain[4],compGain[5]);
    compGain[5]=compGain[4]+band6OwnDetectorMix*(band6ControlledGain-compGain[4]);
    if(activityTracking)currentBand6ControlGain=compGain[5]/std::max(compGain[4],tiny);
    std::array<double,6> compBandL=sourceL,compBandR=sourceR;
    if(mbClipMix>0){
        compBandL[2]=mbClipL[0].run(compBandL[2],mbWorkRef*.56,mbClipMix*.55,.42,dc3Amt,distCancelA);compBandR[2]=mbClipR[0].run(compBandR[2],mbWorkRef*.56,mbClipMix*.55,.42,dc3Amt,distCancelA);
        compBandL[3]=mbClipL[1].run(compBandL[3],mbWorkRef*.48,mbClipMix*.75,.36,dc4Amt,distCancelA);compBandR[3]=mbClipR[1].run(compBandR[3],mbWorkRef*.48,mbClipMix*.75,.36,dc4Amt,distCancelA);
        compBandL[4]=mbClipL[2].run(compBandL[4],mbWorkRef*.40,mbClipMix,.30,dc5Amt,distCancelA);compBandR[4]=mbClipR[2].run(compBandR[4],mbWorkRef*.40,mbClipMix,.30,dc5Amt,distCancelA);
        compBandL[5]=mbClipL[3].run(compBandL[5],mbWorkRef*.32,mbClipMix,.24,dc6Amt,distCancelA);compBandR[5]=mbClipR[3].run(compBandR[5],mbWorkRef*.32,mbClipMix,.24,dc6Amt,distCancelA);
    }
    std::array<double,6> compProcessedL{},compProcessedR{};
    for(std::size_t i=0;i<6;++i){compProcessedL[i]=compBandL[i]*compGain[i];compProcessedR[i]=compBandR[i]*compGain[i];}
    std::array<double,6> pL{},pR{},limiterGain{};
    if(broadcastDensityActive){
        ++shapeRecoveryCounter;shapeRecoveryTick=shapeRecoveryCounter>=16;if(shapeRecoveryTick)shapeRecoveryCounter=0;
        const std::array<double,3> sourcePeak{absmax2(sourceL[0],sourceR[0])+0.0000001,absmax2(sourceL[1],sourceR[1])+0.0000001,absmax2(sourceL[2],sourceR[2])+0.0000001};
        for(std::size_t i=0;i<3;++i){const double postPeak=absmax2(compProcessedL[i],compProcessedR[i])+0.0000001;shapeCompRatioBlock[i]=std::max(shapeCompRatioBlock[i],sourcePeak[i]/postPeak);}
        if(shapeRecoveryTick){
            const std::array<double,3> allowance{.18,.18,.25},scale{.55,.62,.18},cap{2.30,2.45,.65};
            for(std::size_t i=0;i<3;++i){const double lossDb=std::max(0.0,linToDb(shapeCompRatioBlock[i])-allowance[i]);const double targetDb=std::min(lossDb*scale[i],cap[i])*mbShape;const double coefficient=targetDb<shapeCompRecoveryDb[i]?shapeRecoveryReleaseBlock:shapeRecoveryAttackBlock;shapeCompRecoveryDb[i]+=coefficient*(targetDb-shapeCompRecoveryDb[i]);compRecoveryGain[i]=dbToLin(shapeCompRecoveryDb[i]);shapeCompRatioBlock[i]=1.0;}
        }
        for(std::size_t i=0;i<3;++i){compProcessedL[i]*=compRecoveryGain[i];compProcessedR[i]*=compRecoveryGain[i];}
        std::array<double,6> limiterProcessedL{},limiterProcessedR{};
        for(std::size_t i=0;i<6;++i){limiterGain[i]=mbEvent[i].run(absmax2(sourceL[i],sourceR[i]),limiterWorkDb[i],limiterQuietThreshold[i],mbEventAttack,sampleRate,mbEventMinimumRelease,mbEventMaximumRelease);limiterProcessedL[i]=sourceL[i]*limiterGain[i];limiterProcessedR[i]=sourceR[i]*limiterGain[i];}
        limiterProcessedL[3]*=mbPresencePost;limiterProcessedR[3]*=mbPresencePost;limiterProcessedL[4]*=mbPresencePost;limiterProcessedR[4]*=mbPresencePost;limiterProcessedL[5]*=mbBrilliancePost;limiterProcessedR[5]*=mbBrilliancePost;
        for(std::size_t i=0;i<6;++i){limiterProcessedL[i]=limiterBandClip(limiterProcessedL[i],limiterWork[i],.35,.75);limiterProcessedR[i]=limiterBandClip(limiterProcessedR[i],limiterWork[i],.35,.75);}
        for(std::size_t i=0;i<3;++i){const double postPeak=absmax2(limiterProcessedL[i],limiterProcessedR[i])+0.0000001;shapeLimiterRatioBlock[i]=std::max(shapeLimiterRatioBlock[i],sourcePeak[i]/postPeak);}
        if(shapeRecoveryTick){
            const std::array<double,3> allowance{.18,.18,.25},scale{.62,.70,.20},cap{2.60,2.75,.75};
            for(std::size_t i=0;i<3;++i){const double lossDb=std::max(0.0,linToDb(shapeLimiterRatioBlock[i])-allowance[i]);const double targetDb=std::min(lossDb*scale[i],cap[i])*mbShape;const double coefficient=targetDb<shapeLimiterRecoveryDb[i]?shapeRecoveryReleaseBlock:shapeRecoveryAttackBlock;shapeLimiterRecoveryDb[i]+=coefficient*(targetDb-shapeLimiterRecoveryDb[i]);limiterRecoveryGain[i]=dbToLin(shapeLimiterRecoveryDb[i]);shapeLimiterRatioBlock[i]=1.0;}
        }
        for(std::size_t i=0;i<3;++i){limiterProcessedL[i]*=limiterRecoveryGain[i];limiterProcessedR[i]*=limiterRecoveryGain[i];}
        for(std::size_t i=0;i<6;++i){limiterProcessedL[i]*=mbLimiterForkCalibrationGain;limiterProcessedR[i]*=mbLimiterForkCalibrationGain;pL[i]=compProcessedL[i]*mbCompKeep+limiterProcessedL[i]*mbCompLimiter;pR[i]=compProcessedR[i]*mbCompKeep+limiterProcessedR[i]*mbCompLimiter;}
        for(std::size_t i=0;i<6;++i)shapePowerAccum[i]+=(pL[i]*pL[i]+pR[i]*pR[i])*.5;
        ++shapeBlockCounter;
        if(shapeBlockCounter>=32){
            shapeBlockCounter=0;
            for(std::size_t i=0;i<6;++i){shapeLevel[i]+=shapeServoLevelBlock*(shapePowerAccum[i]*.03125-shapeLevel[i]);shapePowerAccum[i]=0.0;}
            const double referenceLevel=std::sqrt(std::max((shapeLevel[2]+shapeLevel[3])*.5,0.000000000001));
            std::array<double,6> ratioDb{};for(std::size_t i=0;i<6;++i)ratioDb[i]=linToDb(std::sqrt(std::max(shapeLevel[i],0.000000000001))/referenceLevel);
            const double presenceBiasDb=clamp(presenceDb,-6.0,6.0),brillianceBiasDb=clamp(brillianceDb,-6.0,6.0);
            const std::array<double,6> targetProfileDb{-1.8,-.7,-.3,0.0,-2.2+presenceBiasDb*.24,-4.6+brillianceBiasDb*.26};
            std::array<double,6> servoTargetDb{};
            servoTargetDb[0]=(clamp((targetProfileDb[0]-ratioDb[0])*.34,-1.75,2.40)+2.5)*mbShape;
            servoTargetDb[1]=(clamp((targetProfileDb[1]-ratioDb[1])*.36,-1.65,2.55)+.9)*mbShape;
            servoTargetDb[2]=clamp((targetProfileDb[2]-ratioDb[2])*.16,-.60,.55)*mbShape;
            servoTargetDb[3]=clamp((targetProfileDb[3]-ratioDb[3])*.10,-.40,.40)*mbShape;
            servoTargetDb[4]=clamp((targetProfileDb[4]-ratioDb[4])*.18,-1.10,1.15)*shapeHighAmount;
            servoTargetDb[5]=clamp((targetProfileDb[5]-ratioDb[5])*.18,-1.35,1.35)*shapeHighAmount;
            for(std::size_t i=0;i<6;++i){shapeServoDb[i]+=shapeServoGainBlock*(servoTargetDb[i]-shapeServoDb[i]);shapeServoGain[i]=dbToLin(shapeServoDb[i]);}
        }
        for(std::size_t i=0;i<6;++i){pL[i]*=shapeServoGain[i];pR[i]*=shapeServoGain[i];}
        pL[3]*=presenceEdgeRecoveryGain;pR[3]*=presenceEdgeRecoveryGain;
        pL[4]*=presenceBodyRecoveryGain;pR[4]*=presenceBodyRecoveryGain;
        pL[5]*=brillianceRecoveryGain;pR[5]*=brillianceRecoveryGain;
        if(activityTracking){std::array<double,6> blendedGain{};for(std::size_t i=0;i<6;++i)blendedGain[i]=compGain[i]*mbCompKeep+limiterGain[i]*mbCompLimiter;currentDensityGain=*std::min_element(blendedGain.begin(),blendedGain.end());currentBand6Gain=blendedGain[5];}
    }else{
        pL=compProcessedL;pR=compProcessedR;
        if(activityTracking){currentDensityGain=*std::min_element(compGain.begin(),compGain.end());currentBand6Gain=compGain[5];}
    }
    if(effectiveSnubberLookahead>0){int read=snubWrite-effectiveSnubberLookahead;if(read<0)read+=snubBufferLength;std::array<double,6>dL{},dR{};for(size_t i=0;i<6;i++){dL[i]=snubL[i][read];dR[i]=snubR[i][read];snubL[i][snubWrite]=pL[i];snubR[i][snubWrite]=pR[i];}pL=dL;pR=dR;snubWrite=(snubWrite+1)%snubBufferLength;}
    /* Podcast has upperSnubber=0; retain exact generic behavior by running source algorithm only when active. */
    if(upperSnubber>0){const double usAmt=upperSnubber,lvl4=absmax2(pL[3],pR[3]),lvl5=absmax2(pL[4],pR[4]),lvl6=absmax2(pL[5],pR[5]);const double fast4=ubFast4.lp(lvl4,upperSnubFastA),fast5=ubFast5.lp(lvl5,upperSnubFastA),fast6=ubFast6.lp(lvl6,upperSnubFastA),slow4=ubSlow4.lp(lvl4,upperSnubSlowA),slow5=ubSlow5.lp(lvl5,upperSnubSlowA),slow6=ubSlow6.lp(lvl6,upperSnubSlowA),onset4=clamp((fast4-slow4*1.22)/std::max(slow4*.80+tiny,tiny),0,1),onset5=clamp((fast5-slow5*1.18)/std::max(slow5*.72+tiny,tiny),0,1),onset6=clamp((fast6-slow6*1.15)/std::max(slow6*.66+tiny,tiny),0,1),spike4=clamp((lvl4-slow4*1.20)/std::max(slow4*1.20+tiny,tiny),0,1),spike5=clamp((lvl5-slow5*1.16)/std::max(slow5*1.05+tiny,tiny),0,1),spike6=clamp((lvl6-slow6*1.12)/std::max(slow6*.95+tiny,tiny),0,1),d4=std::max(std::abs(pL[3]-usPrev4L),std::abs(pR[3]-usPrev4R)),d5=std::max(std::abs(pL[4]-usPrev5L),std::abs(pR[4]-usPrev5R)),d6=std::max(std::abs(pL[5]-usPrev6L),std::abs(pR[5]-usPrev6R)),c4=std::max(std::abs(pL[3]-2*usPrev4L+usPrev24L),std::abs(pR[3]-2*usPrev4R+usPrev24R)),c5=std::max(std::abs(pL[4]-2*usPrev5L+usPrev25L),std::abs(pR[4]-2*usPrev5R+usPrev25R)),c6=std::max(std::abs(pL[5]-2*usPrev6L+usPrev26L),std::abs(pR[5]-2*usPrev6R+usPrev26R));usPrev24L=usPrev4L;usPrev24R=usPrev4R;usPrev25L=usPrev5L;usPrev25R=usPrev5R;usPrev26L=usPrev6L;usPrev26R=usPrev6R;usPrev4L=pL[3];usPrev4R=pR[3];usPrev5L=pL[4];usPrev5R=pR[4];usPrev6L=pL[5];usPrev6R=pR[5];const double dslow4=ubDslow4.lp(d4,upperSnubDeltaA),dslow5=ubDslow5.lp(d5,upperSnubDeltaA),dslow6=ubDslow6.lp(d6,upperSnubDeltaA),cslow4=ubCslow4.lp(c4,upperSnubCurveA),cslow5=ubCslow5.lp(c5,upperSnubCurveA),cslow6=ubCslow6.lp(c6,upperSnubCurveA),shape4=std::max(clamp((d4-dslow4*1.75)/std::max(dslow4*2.60+tiny,tiny),0,1),clamp((c4-cslow4*1.85)/std::max(cslow4*2.75+tiny,tiny),0,1)),shape5=std::max(clamp((d5-dslow5*1.70)/std::max(dslow5*2.35+tiny,tiny),0,1),clamp((c5-cslow5*1.78)/std::max(cslow5*2.45+tiny,tiny),0,1)),shape6=std::max(clamp((d6-dslow6*1.65)/std::max(dslow6*2.20+tiny,tiny),0,1),clamp((c6-cslow6*1.72)/std::max(cslow6*2.30+tiny,tiny),0,1));double ng4=clamp(onset4*shape4*(.25+.75*spike4),0,1),ng5=clamp(onset5*shape5*(.22+.78*spike5),0,1),ng6=clamp(onset6*shape6*(.18+.82*spike6)*(.20+.80*std::max(onset5,ng5)),0,1);ng4=ubGate4.run(ng4,upperSnubGainAttack,upperSnubGainRelease);ng5=ubGate5.run(ng5,upperSnubGainAttack,upperSnubGainRelease);ng6=ubGate6.run(ng6,upperSnubGainAttack,upperSnubGainRelease);const double th4=std::max(ceiling*.105,std::min(ceiling*(.46-.07*usAmt),slow4*(1.36-.22*usAmt))),th5=std::max(ceiling*.080,std::min(ceiling*(.36-.075*usAmt),slow5*(1.26-.24*usAmt))),th6=std::max(ceiling*.060,std::min(ceiling*(.30-.060*usAmt),slow6*(1.18-.18*usAmt)));pL[3]=purePeakRound(pL[3],th4,usAmt*ng4*.62,.42+.10*usAmt);pR[3]=purePeakRound(pR[3],th4,usAmt*ng4*.62,.42+.10*usAmt);pL[4]=purePeakRound(pL[4],th5,usAmt*ng5*.92,.48+.14*usAmt);pR[4]=purePeakRound(pR[4],th5,usAmt*ng5*.92,.48+.14*usAmt);const double lim6Gain=ubLim6.linkedLimiter(lvl6,th6,upperSnubGainAttack,upperSnubGainRelease),tg6=1-usAmt*ng6*.62*(1-lim6Gain);pL[5]*=tg6;pR[5]*=tg6;}
    double sumL=0,sumR=0;for(size_t i=0;i<6;i++){sumL+=pL[i];sumR+=pR[i];}if(recombControl>0){l=sumL+recombControl*(softClipKnee(sumL,recombClipThresh,recombClipKnee)-sumL);r=sumR+recombControl*(softClipKnee(sumR,recombClipThresh,recombClipKnee)-sumR);}else{l=sumL;r=sumR;}if(transitionFill>0){l=transitionPeakL.run(l);r=transitionPeakR.run(r);}if(lowBassFloor>0){l=lowFloorL.run(l);r=lowFloorR.run(r);}if(postXt2SmoothDriveAmt>.0000001){l=postXt2RoundL.run(l,postXt2SmoothDriveAmt)*postXt2SmoothRecoveryGain;r=postXt2RoundR.run(r,postXt2SmoothDriveAmt)*postXt2SmoothRecoveryGain;}double mid=(l+r)*.5,side=(l-r)*.5;if(sideScale<1.0){side*=sideScale;}else if(sideScale>1.0000001){const double extraRequest=sideScale-1.0;side*=1.0+extraRequest*adaptiveStereoWidthGain(std::abs(mid),std::abs(side),extraRequest);}if(stereoMode==1)side=softClipKnee(side,std::max(.05,std::abs(mid)*.90+.08),.30);l=mid+side;r=mid-side;l*=preFinalDriveGain;r*=preFinalDriveGain;if(finalThresholdDriveS<=0)finalThresholdDriveS=finalThresholdDriveTarget;finalThresholdDriveS=finalThresholdDriveTarget+finalThresholdSmooth*(finalThresholdDriveS-finalThresholdDriveTarget);const double finalThresholdMakeupCancel=finalThresholdDriveS>1&&finalThresholdMakeup<.999999?std::exp(-std::log(finalThresholdDriveS)*(1-finalThresholdMakeup)):1;l*=finalThresholdDriveS;r*=finalThresholdDriveS;if(finalThresholdDriveS>1.000001){const double det=absmax2(l,r),target=det>clipRef?clipRef/std::max(det,tiny):1;finalThresholdGuardGain=target<finalThresholdGuardGain?target:target+clipRelease*(finalThresholdGuardGain-target);l*=finalThresholdGuardGain;r*=finalThresholdGuardGain;}else finalThresholdGuardGain=1+clipRelease*(finalThresholdGuardGain-1);const double clipFullEnv=finalFullEnv.run(absmax2(l,r),clipAttack,clipRelease),levelFactor=clamp((clipFullEnv-ceiling*.55)/std::max(ceiling*.35,tiny),0,1),protectDb=peakOnlyFinalLimiter?0:-2.0*clipRestraint*levelFactor,dynamicClipGain=protectDb<0?dbToLin(protectDb):1,finalDriveGain=peakOnlyFinalLimiter?1:dynamicClipGain;l*=finalDriveGain;r*=finalDriveGain;const double preGain=preclip.linkedLimiter(absmax2(l,r),prelimitThresh,clipAttack,clipRelease),preTGain=1-prelimitMix*(1-preGain);if(activityTracking)currentFinalGain=std::min({finalThresholdGuardGain,dynamicClipGain,preTGain});l*=preTGain;r*=preTGain;const double clipInL=l,clipInR=r;double clipL=clipInL,clipR=clipInR;if(!peakOnlyFinalLimiter){clipL=softClipKnee(softClipKnee(clipInL,clipStage1,clipKnee1),clipStage2,clipKnee2);clipR=softClipKnee(softClipKnee(clipInR,clipStage1,clipKnee1),clipStage2,clipKnee2);}if(dcCancel>0){const double dl=distLpfL.lp(clipL-clipInL,distCancelA),dr=distLpfR.lp(clipR-clipInR,distCancelA);l=clipL-dl*dcCancel*.45;r=clipR-dr*dcCancel*.45;}else{l=clipL;r=clipR;}if(topFilterMode==1){l=lpf15_1L.run(l);r=lpf15_1R.run(r);}else if(topFilterMode>=2){l=lpf15_2L.run(lpf15_1L.run(l));r=lpf15_2R.run(lpf15_1R.run(r));}l*=finalThresholdMakeupCancel;r*=finalThresholdMakeupCancel;if(smoothDriveRounderAmt>.0000001){l=finalRoundL.run(l,smoothDriveRounderAmt);r=finalRoundR.run(r,smoothDriveRounderAmt);}l*=outputGain;r*=outputGain;const double ovL=fcsResL.lp(l-hardLimit(l,fcsThreshSetting),fcsResidueA),ovR=fcsResR.lp(r-hardLimit(r,fcsThreshSetting),fcsResidueA);if(effectiveFinalLookahead>0){int read=fcsWrite-effectiveFinalLookahead;if(read<0)read+=fcsBufferLength;const double delayedL=fcsBufL[read],delayedR=fcsBufR[read],delayedOvL=fcsBufOL[read],delayedOvR=fcsBufOR[read];fcsBufL[fcsWrite]=l;fcsBufR[fcsWrite]=r;fcsBufOL[fcsWrite]=ovL;fcsBufOR[fcsWrite]=ovR;fcsWrite=(fcsWrite+1)%fcsBufferLength;l=delayedL-delayedOvL*overshootAmt;r=delayedR-delayedOvR*overshootAmt;}else{l-=ovL*overshootAmt;r-=ovR*overshootAmt;}l=hardLimit(l,ceiling);r=hardLimit(r,ceiling);if(hybridTotalDelaySamples>0)processHybrid(l,r);processDelivery(l,r);l=hardLimit(l,ceiling);r=hardLimit(r,ceiling);const float deliveryCeiling=std::nextafter(static_cast<float>(ceiling),0.0f);const float outL=std::clamp(static_cast<float>(l),-deliveryCeiling,deliveryCeiling),outR=std::clamp(static_cast<float>(r),-deliveryCeiling,deliveryCeiling);return{outL,outR};
}
void OptiLabCore::processInterleaved(float*samples,std::size_t frames,std::size_t channels){if(!samples||channels==0)return;for(size_t frame=0;frame<frames;frame++){float left=samples[frame*channels],right=channels>1?samples[frame*channels+1]:left;auto p=processSample(left,right);samples[frame*channels]=p.first;if(channels>1){samples[frame*channels+1]=p.second;for(size_t ch=2;ch<channels;ch++)samples[frame*channels+ch]=0;}}}
void OptiLabCore::processPlanar(float*left,float*right,std::size_t frames){if(!left)return;for(size_t frame=0;frame<frames;frame++){const float l=left[frame],r=right?right[frame]:l;const auto p=processSample(l,r);left[frame]=p.first;if(right)right[frame]=p.second;}}
