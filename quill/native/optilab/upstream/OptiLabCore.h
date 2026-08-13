#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <utility>
#include <vector>

class OptiLabCore {
public:
    enum class Mode {
        PodcastLeveler = 0,
        StreamPolish = 1,
        SmoothLimiter = 2,
    };

    struct Parameters {
        Mode mode = Mode::PodcastLeveler;
        double inputDriveDb = 3.5;
        double autoAdaptPct = 0.0;
    };

    struct Activity {
        double agcGain = 1.0;
        double densityGain = 1.0;
        double band6Gain = 1.0;
        double band6ControlGain = 1.0;
        double finalGain = 1.0;
        double foundationFeedbackDb = 0.0;
        double effectiveFinalThresholdDb = 0.0;
        double adaptAgcTargetDb = -17.0;
        double finalBackoffDb = 0.0;
    };

    static Parameters defaultParameters(Mode mode) noexcept;

    void prepare(double newSampleRate);
    void setParameters(const Parameters& newParameters);
    Parameters parameters() const { return params; }
    Activity activity() const noexcept;
    void setActivityTracking(bool enabled) noexcept { activityTracking = enabled; }
    std::size_t latencySamples() const { return pathDelay; }
    void reset();

    std::pair<float, float> processSample(float left, float right);
    void processPlanar(float* left, float* right, std::size_t frames);
    void processInterleaved(float* samples, std::size_t frames, std::size_t channels);

private:
    struct OnePole {
        double z = 0.0;
        double z1 = 0.0;
        double z2 = 0.0;
        double lp(double x, double a);
        double lp2(double x, double a);
        double hp(double x, double a);
        void reset();
    };
    struct Allpass1 {
        double x1 = 0.0;
        double y1 = 0.0;
        double run(double x, double c);
        void reset();
    };
    struct PeakEnv {
        double e = 0.0;
        double run(double det, double attack, double release);
        double set(double value);
    };
    struct GainCell {
        double env = 0.0;
        double gain = 1.0;
        double bandLimitPd(double det, double thresh, double attack, double relBase, double relSlow, double pdAmt);
        double bandLimitPdSoft(double det, double thresh, double attack, double relBase, double relSlow,
                               double pdAmt, double ratio, double knee, double minGain);
        double linkedLimiter(double det, double thresh, double attack, double release);
    };
    struct EventCell {
        double env = 0.0;
        double gain = 1.0;
        double run(double det, double threshDb, double quietThreshold, double attack, double sampleRate,
                   double minimumRelease, double maximumRelease);
    };
    struct SmoothRounder {
        double prevSat = 0.0;
        double run(double x, double amt);
        void reset();
    };
    struct DcClipper {
        double dcZ = 0.0;
        double run(double x, double th, double amt, double kneeMul, double cancelAmt, double a);
        void reset();
    };
    struct BassClipper {
        double z1 = 0.0;
        double z2 = 0.0;
        double run(double x, double th, double amt, double kneeMul, double drive, double resMix, double a);
        void reset();
    };
    struct Biquad {
        double a0 = 1.0;
        double a1 = 0.0;
        double a2 = 0.0;
        double b1 = 0.0;
        double b2 = 0.0;
        double x1 = 0.0;
        double x2 = 0.0;
        double y1 = 0.0;
        double y2 = 0.0;
        void setLowpass(double freq, double q, double sampleRate);
        void setPeak(double freq, double q, double gainDb, double sampleRate);
        void setLowShelf(double freq, double slope, double gainDb, double sampleRate);
        void copyCoefficientsFrom(const Biquad& source);
        double run(double x);
        void reset();
    };

    struct FoundationGuard {
        Biquad lp70L, lp70R, lp250L, lp250R;
        Biquad lp420L, lp420R, lp3700L, lp3700R;
        Biquad shelfL, shelfR, bodyL, bodyR;
        PeakEnv deepFast, usefulFast, midFast;
        PeakEnv deepSlow, usefulSlow, midSlow;
        bool primed = false;
        std::size_t ageSamples = 0;
        int controlCounter = 15;
        int coefficientCounter = 63;
        double fastDeepBoostEvidenceDb = 0.0;
        double fastUsefulBoostEvidenceDb = 0.0;
        double fastDeepCutEvidenceDb = 0.0;
        double fastUsefulCutEvidenceDb = 0.0;
        double deepBoostStateDb = 0.0;
        double usefulBoostStateDb = 0.0;
        double deepCutStateDb = 0.0;
        double usefulCutStateDb = 0.0;
        double deepTargetDb = 0.0;
        double usefulTargetDb = 0.0;
        double deepTargetGain = 1.0;
        double usefulTargetGain = 1.0;
        double voiceTarget = 1.0;
        double voiceGain = 1.0;
        double detAttack = 0.0;
        double detRelease = 0.0;
        double slowAttack = 0.0;
        double slowRelease = 0.0;
        double fastBoostAttackTick = 0.0;
        double fastBoostReleaseTick = 0.0;
        double fastCutAttackTick = 0.0;
        double fastCutReleaseTick = 0.0;
        double boostAttackTick = 0.0;
        double boostReleaseTick = 0.0;
        double boostSuppressTick = 0.0;
        double cutAttackTick = 0.0;
        double cutReleaseTick = 0.0;
        double cutSuppressTick = 0.0;
        std::size_t cutHoldoffSamples = 0;
        double voiceReturn = 0.0;
        double voiceWithdraw = 0.0;
        double boostScale = 0.0;
        double cutAuthority = 0.0;
        double link = 0.0;
        double withdrawAuthority = 0.0;

        // Closed-loop foundation refinement. The detector and actuator remain the
        // existing Foundation Guard; these scalars only feed back the already
        // computed post-bass density bands one control block later.
        double feedbackB1Accum = 0.0;
        double feedbackB2Accum = 0.0;
        std::size_t feedbackCount = 0;
        double feedbackRatioDb = -120.0;
        double feedbackServoDb = 0.0;
        double feedbackBurden = 0.0;

        // Rumble veto reuses the low component already rejected by Stream's
        // 42.5 Hz high-pass. It never creates another audio crossover.
        double rumbleSubAccum = 0.0;
        double rumbleTotalAccum = 0.0;
        std::size_t rumbleCount = 0;
        double rumbleRatioDb = -120.0;
        double rumbleSubEnv = 0.0;
        double rumbleTotalEnv = 0.0;
        double rumbleState = 0.0;

        double feedbackAttackTick = 0.0;
        double feedbackReleaseTick = 0.0;
        double feedbackFastReleaseTick = 0.0;
        double feedbackBurdenAttackTick = 0.0;
        double feedbackBurdenReleaseTick = 0.0;
        double rumbleEnergyTick = 0.0;
        double rumbleAttackTick = 0.0;
        double rumbleReleaseTick = 0.0;
        double feedbackMaxAssistDb = 12.0;
        void reset();
    };

    static double dbToLin(double db);
    static double linToDb(double x);
    static double clamp(double x, double lo, double hi);
    static double smoothstep01(double x);
    static double adaptiveBassBoostCurve(double x);
    static double adaptiveBassCutCurve(double x);
    static double absmax2(double a, double b);
    static double softClipKnee(double x, double th, double kneeMul);
    static double limiterBandClip(double x, double limit, double amount, double soft);
    static double purePeakRound(double x, double th, double amt, double driveMul);
    static double hardLimit(double x, double ceiling);
    static double hybridShaveToLimit(double x, double limit, double depthDb);
    double hybridEventTonalCorrelation(std::int64_t nowAbs) const;
    double apCoeff(double freq) const;
    void processHybrid(double& l, double& r);
    void processDelivery(double& l, double& r);
    double adaptiveStereoWidthGain(double midDet, double sideDet, double extraRequest);
    std::pair<double, double> processFoundationGuard(double preL, double preR, double boostedL, double boostedR);
    void applyModeAndDerivedParameters();
    void resetPhaseState();
    Parameters params;
    double sampleRate = 48000.0;
    int lastMode = -1;

    static constexpr int fcsBufferLength = 512;
    static constexpr int snubBufferLength = 512;
    static constexpr int masterBufferLength = 4096;
    std::array<double, fcsBufferLength> fcsBufL{};
    std::array<double, fcsBufferLength> fcsBufR{};
    std::array<double, fcsBufferLength> fcsBufOL{};
    std::array<double, fcsBufferLength> fcsBufOR{};
    int fcsWrite = 0;

    // One transparent reconstruction-aware delivery limiter owns final ceiling safety.
    // The detector is oversampled; the audio path itself remains at the host rate.
    static constexpr int deliveryBufferLength = 2048;
    static constexpr int deliveryDetectorTaps = 13;
    static constexpr int deliveryDetectorPhases = 8;
    static constexpr int deliveryDetectorDelaySamples = 6;
    std::array<double, deliveryBufferLength> deliveryBufL{};
    std::array<double, deliveryBufferLength> deliveryBufR{};
    std::array<double, deliveryBufferLength> deliveryRequired{};
    std::array<double, deliveryDetectorTaps> deliveryHistL{};
    std::array<double, deliveryDetectorTaps> deliveryHistR{};
    std::array<double, deliveryDetectorTaps * deliveryDetectorPhases> deliveryCoeff{};
    int deliveryWrite = 0;
    int deliveryLookaheadSamples = 0;
    int deliveryAnticipationSamples = 1;
    double deliveryGain = 1.0;
    double deliveryRelease = 0.0;
    double deliveryTarget = 1.0;

    static constexpr int hybridHistoryLength = 16384;
    static constexpr int hybridEnergyLength = 8192;
    std::vector<double> hybridRawL = std::vector<double>(hybridHistoryLength, 0.0);
    std::vector<double> hybridRawR = std::vector<double>(hybridHistoryLength, 0.0);
    std::vector<double> hybridCandidateL = std::vector<double>(hybridHistoryLength, 0.0);
    std::vector<double> hybridCandidateR = std::vector<double>(hybridHistoryLength, 0.0);
    std::vector<double> hybridShavedL = std::vector<double>(hybridHistoryLength, 0.0);
    std::vector<double> hybridShavedR = std::vector<double>(hybridHistoryLength, 0.0);
    std::vector<double> hybridRequiredGain = std::vector<double>(hybridHistoryLength, 1.0);
    std::vector<double> hybridBurden = std::vector<double>(hybridHistoryLength, 1.0);
    std::vector<double> hybridEventGate = std::vector<double>(hybridHistoryLength, 0.0);
    std::vector<double> hybridWorkLimit = std::vector<double>(hybridHistoryLength, 1.0);
    std::vector<double> hybridMakeup = std::vector<double>(hybridHistoryLength, 1.0);
    std::vector<double> hybridAttackShape = std::vector<double>(hybridHistoryLength, 1.0);
    std::vector<double> hybridRefEnergy = std::vector<double>(hybridEnergyLength, 0.0);
    std::vector<double> hybridDeltaEnergy = std::vector<double>(hybridEnergyLength, 0.0);
    int hybridWrite = 0, hybridEnergyWrite = 0, hybridEnergyCount = 0;
    std::vector<std::uint8_t> hybridRequiredActive = std::vector<std::uint8_t>(hybridHistoryLength, 0);
    int hybridLimiterActiveCount = 0;
    bool hybridLimiterWindowTracked = false;
    int hybridBurdenWindowSamples = 1, hybridClassificationSamples = 0, hybridLimiterLookaheadSamples = 0, hybridTotalDelaySamples = 0;
    int hybridPeriodMinSamples = 2, hybridPeriodMaxSamples = 3;
    std::int64_t hybridSampleClock = 0;
    bool hybridCandidateActivePrev = false;
    std::int64_t hybridEventStartAbs = -1;
    int hybridEventStartRing = 0;
    double hybridEventCorrelation = 0.0;
    std::int64_t hybridOnset1 = -1000000000LL, hybridOnset2 = -1000000000LL, hybridOnset3 = -1000000000LL;
    double hybridRefEnergySum = 0.0, hybridDeltaEnergySum = 0.0, hybridBurdenAccept = 1.0;
    double hybridBurdenAttack = 0.0, hybridBurdenRelease = 0.0, hybridLimiterRelease = 0.0, hybridLimiterGain = 1.0;
    std::array<std::array<double, snubBufferLength>, 6> snubL{};
    std::array<std::array<double, snubBufferLength>, 6> snubR{};
    int snubWrite = 0;
    std::array<double, masterBufferLength> masterBufL{};
    std::array<double, masterBufferLength> masterBufR{};
    int masterWrite = 0;
    std::size_t pathDelay = 0;

    double inputGain = 1.0, agcDrive = 1.0, densityAudioGain = 1.0, densityDetectorGain = 1.0;
    double densityClipDrive = 1.0, presenceGain = 1.0, brillianceGain = 1.0, clipDriveMb = 1.0, clipDriveFull = 1.0;
    double ceiling = 1.0, finalThresholdDriveTarget = 1.0, finalThresholdDriveS = 1.0, finalThresholdGuardGain = 1.0;
    double finalThresholdMakeup = 1.0, smoothDriveRounderAmt = 0.0, postAgcSmoothDriveAmt = 0.0, postXt2SmoothDriveAmt = 0.0;
    double postAgcSmoothRecoveryGain = 1.0, postXt2SmoothRecoveryGain = 1.0, preFinalDriveGain = 1.0, outputGain = 1.0;
    double mbClipMix = 0.0, dcCancel = 0.0, dc3Amt = 0.0, dc4Amt = 0.0, dc5Amt = 0.0, dc6Amt = 0.0;
    bool broadcastDensityActive = false;
    double mbShape = 0.0, shapeHighAmount = 0.0, mbCompLimiter = 0.0, mbCompKeep = 1.0;
    double mbLimiterForkCalibrationGain = 1.0, mbPresencePost = 1.0, mbBrilliancePost = 1.0;
    double presenceEdgeRecoveryGain = 1.0, presenceBodyRecoveryGain = 1.0, brillianceRecoveryGain = 1.0;
    std::array<double,6> limiterWorkDb{}, limiterWork{}, limiterQuietThreshold{};
    double overshootAmt = 0.0, recombControl = 0.0, pdRelease = 0.0, upperSnubber = 0.0, gateReopenStrength = 0.0, sideScale = 1.0;
    double widthMidFast = 0.0, widthMidSlow = 0.0, widthMidEnv = 0.0, widthSideEnv = 0.0, widthAdaptiveGain = 0.0;
    double widthMidFastAttack = 0.0, widthMidFastRelease = 0.0, widthMidSlowAttack = 0.0, widthMidSlowRelease = 0.0;
    double widthLevelAttack = 0.0, widthLevelRelease = 0.0, widthGainReduce = 0.0, widthGainRestore = 0.0;

    double inputTrimDb = 0.0, phaseRotatePct = 0.0; int subsonicHpf = 0;
    double agcAmountPct = 0.0, agcDriveDb = 0.0, releaseTime = 6.0, pdReleasePct = 0.0;
    double gateThresholdDb = -70.0, gateReopenSpeedMs = 50.0, gateReopenStrengthPct = 0.0, postAgcSmoothDrivePct = 0.0;
    double bassCouplingPct = 0.0, bassEqDb = 0.0, bassScReliefPct = 0.0, lowBassFloorPct = 0.0, lowCoherencePct = 0.0;
    double lowReleaseStabPct = 0.0, transitionFillPct = 0.0, adaptiveBassCouplingPct = 0.0, bassClipPct = 0.0, bassClipDensityPct = 0.0;
    double densityDb = 0.0, xt2AmountPct = 0.0, presenceDb = 0.0, brillianceDb = 0.0, adaptiveTopCouplingPct = 0.0;
    int crossoverModel = 2; double mbClipPct = 0.0, mbShapePct = 0.0, mbLimiterDepthPct = 50.0, mbCompLimiterPct = 0.0;
    double clipDriveDb = 0.0, recombControlPct = 0.0, dcCancelPct = 0.0;
    double upperSnubberPct = 0.0, snubberLookaheadMs = 0.0, postXt2SmoothDrivePct = 0.0; int stereoMode = 0;
    double stereoWidthPct = 100.0, preFinalDriveDb = 0.0; int clipperStyle = 0;
    double preLimiterPct = 100.0, clipRestraintPct = 100.0, overshootPct = 100.0, lookaheadMs = 0.0;
    double finalThresholdDb = 0.0, finalThresholdMakeupPct = 0.0, clipCeilingDb = -0.1; int topFilterMode = 0;
    double outputTrimDb = 0.0, smoothDriveRounderPct = 0.0; int processorMode = 0;

    int phaseMode = 0, phaseModeLast = -1, phaseStages = 0, effectiveSnubberLookahead = 0, effectiveFinalLookahead = 0, masteringLookaheadSamples = 0;
    double agcMix = 0.0, agcDownMix = 0.0, xt2Mix = 0.0, adaptiveTopCoupling = 0.0, bassCoupling = 0.0;
    double bassScRelief = 0.0, lowCoherence = 0.0, lowReleaseStab = 0.0, transitionFill = 0.0, lowBassFloor = 0.0;
    double adaptiveBassCoupling = 0.0, foundationMix = 0.0, hybridMix = 0.0, streamHpfMix = 0.0, finalStyleBlend = 0.0, bassClip = 0.0, bassClipDensity = 0.0, prelimitMix = 1.0, clipRestraint = 1.0;
    double band6OwnDetectorMix = 0.0, streamAgcLiftDb = 0.0, finalBackoffMix = 0.0;
    bool peakOnlyFinalLimiter = false; double prelimitThresh = 1.0, fcsThreshSetting = 1.0;

    double agcEnvAttack=0,agcGainAttack=0,agcRelease=0,agcReleaseSlow=0,bandAttack=0,upperBandAttack=0,upperMidBandAttack=0;
    double bandRelease=0,bandReleaseSlow=0,lowBandRelease=0,lowBandReleaseSlow=0,clipAttack=0,clipRelease=0,finalThresholdSmooth=0;
    double recombAttack=0,recombRelease=0,startupActivityRelease=0,masterCatchAttack=0,masterCatchRelease=0,masterEnvAttack=0,masterEnvRelease=0;
    double gateDetectorRelease=0,gateCloseCoeff=0,gateOpenCoeff=0,gateAgcFreezeRelease=0,gateXt2FreezeRelease=0,gateReopenRelease=0;
    double gateReopenEnvRelease=0,gateReopenDecay=0,gateReopenPulseScale=0,gateAgcDriftTarget=0,gateAgcDriftCoeff=0;
    double upperSnubFastA=0,upperSnubSlowA=0,upperSnubDeltaA=0,upperSnubCurveA=0,upperSnubGainAttack=0,upperSnubGainRelease=0;
    double mbEventAttack=0,mbEventMinimumRelease=0,mbEventMaximumRelease=0;
    double shapeRecoveryAttackBlock=0,shapeRecoveryReleaseBlock=0,shapeServoLevelBlock=0,shapeServoGainBlock=0;
    double hpf30A=0,agcSplitA=0,x1A=0,x2A=0,x3A=0,x4A=0,x5A=0,distCancelA=0; std::array<double,12> apC{};
    double agcTarget=0,agcTargetBaseDb=-17,agcLiftStateDb=0,agcLiftAttackBlock=0,agcLiftReleaseBlock=0,agcMaxGain=0,agcMinGain=0,gateLin=0,b1Thresh=0,b2Thresh=0,b3Thresh=0,b4Thresh=0,b5Thresh=0,b6Thresh=0;
    double finalBackoffDb=0,finalFoundationBurden=0,finalBackoffAttackBlock=0,finalBackoffReleaseBlock=0;
    int finalLoadCounter=0;
    double constDb2LinMinus62=0,constDb2LinMinus36=0,clipRef=0,mbWorkRef=0,b1DetScGain=1,b2DetScGain=1;
    double adaptBassSplitA=0,adaptBassDetAttack=0,adaptBassDetRelease=0,adaptBassGainUp=0,adaptBassGainDown=0;
    double adaptBassTargetLow=0.33,adaptBassTargetHigh=0.52,adaptBassMaxBoostDb=0,adaptBassMaxCutDb=0;
    double adaptTopDetAttack=0,adaptTopDetRelease=0,adaptTopGainUp=0,adaptTopGainDown=0,adaptTopEdgeTargetLow=0,adaptTopEdgeTargetHigh=0;
    double adaptTopAirTargetLow=0,adaptTopAirTargetHigh=0,adaptTopPresenceMaxBoostDb=0,adaptTopPresenceMaxCutDb=0,adaptTopAirMaxBoostDb=0,adaptTopAirMaxCutDb=0,adaptTopAirHpA=0;
    double bassClipSplitA=0,bassClipSubhpA=0,bassClipPreResA=0,bassClipPreTh=0,bassClipPreDrive=1,bassClipPreAmt=0,bassClipMakeup=1;
    double recombClipThresh=1,recombClipKnee=.5,clipStage1=1,clipStage2=1,clipKnee1=.5,clipKnee2=.5,fcsResidueA=0;

    double agcLGain=1,agcHGain=1,startupActivity=0,gateProgEnv=0,gateState=0,gateClosedMemory=0,gateReopenEnv=0,gateReopenPulse=0;
    int shapeRecoveryCounter=0; bool shapeRecoveryTick=false; int shapeBlockCounter=0;
    std::array<double,3> shapeCompRecoveryDb{},shapeLimiterRecoveryDb{};
    std::array<double,3> compRecoveryGain{1.0,1.0,1.0},limiterRecoveryGain{1.0,1.0,1.0};
    std::array<double,3> shapeCompRatioBlock{1.0,1.0,1.0},shapeLimiterRatioBlock{1.0,1.0,1.0};
    std::array<double,6> shapeLevel{},shapeServoDb{},shapePowerAccum{};
    std::array<double,6> shapeServoGain{1.0,1.0,1.0,1.0,1.0,1.0};
    double adaptBassGain=1,adaptTopPresenceGain=1,adaptTopAirGain=1,currentAgcLowEffGain=1,currentAgcHighEffGain=1,currentDensityGain=1,currentBand6Gain=1,currentBand6ControlGain=1,currentFinalGain=1;
    bool activityTracking=false; int masterStartupArmed=1,masterStartupAge=0,masterStartupPrimeWindow=0; double masterStartupActiveThresh=0,masterCatchGain=1;

    OnePole hp30L,hp30R; std::array<Allpass1,12> apL,apR; OnePole agcLpL,agcLpR; PeakEnv agcLowEnv,agcHighEnv;
    SmoothRounder postAgcRoundL,postAgcRoundR; PeakEnv masterRawEnv,masterAmpEnv,masterCatchEnv; Biquad bassPeakL,bassPeakR; FoundationGuard foundationGuard;
    OnePole adaptBassLpL,adaptBassLpR; PeakEnv adaptBassEnv,adaptProgEnv; OnePole bassclipSplitL,bassclipSplitR,bassclipHpfL,bassclipHpfR;
    BassClipper bassclipPreL,bassclipPreR; std::array<OnePole,5> xbL,xbR;
    Biquad lr4b1aL,lr4b1aR,lr4b1bL,lr4b1bR,lr4b2aL,lr4b2aR,lr4b2bL,lr4b2bR,lr4b3aL,lr4b3aR,lr4b3bL,lr4b3bR;
    Biquad lr4b4aL,lr4b4aR,lr4b4bL,lr4b4bR,lr4b5aL,lr4b5aR,lr4b5bL,lr4b5bR;
    OnePole adaptTopAirHpL,adaptTopAirHpR; PeakEnv adaptTopEdgeEnv,adaptTopEdgeProgEnv,adaptTopAirEnv,adaptTopAirProgEnv;
    std::array<GainCell,6> lim; std::array<EventCell,6> mbEvent; std::array<DcClipper,4> mbClipL,mbClipR;
    OnePole ubFast4,ubFast5,ubFast6,ubSlow4,ubSlow5,ubSlow6,ubDslow4,ubDslow5,ubDslow6,ubCslow4,ubCslow5,ubCslow6;
    PeakEnv ubGate4,ubGate5,ubGate6; GainCell ubLim6;
    double usPrev4L=0,usPrev4R=0,usPrev24L=0,usPrev24R=0,usPrev5L=0,usPrev5R=0,usPrev25L=0,usPrev25R=0,usPrev6L=0,usPrev6R=0,usPrev26L=0,usPrev26R=0;
    Biquad transitionPeakL,transitionPeakR,lowFloorL,lowFloorR; SmoothRounder postXt2RoundL,postXt2RoundR; PeakEnv finalFullEnv;
    GainCell preclip; OnePole distLpfL,distLpfR; Biquad lpf15_1L,lpf15_1R,lpf15_2L,lpf15_2R; SmoothRounder finalRoundL,finalRoundR;
    OnePole fcsResL,fcsResR;
};
