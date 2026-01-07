package org.brainup.brainup;  // ⚠️ заменишь "yourapp" на своё имя пакета из buildozer.spec

import android.app.Activity;
import android.util.Log;

import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.rewarded.RewardItem;
import com.google.android.gms.ads.rewarded.RewardedAd;
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback;
import com.google.android.gms.ads.FullScreenContentCallback;

import org.kivy.android.PythonActivity;
import org.kivy.android.PythonUtil;

import com.chaquo.python.PyObject;  // нужно если используешь Chaquopy (но Kivy использует jnius)
import org.kivy.android.Python;

public class AdsBridge {
    private static final String TAG = "AdsBridge";
    private final Activity activity;
    private RewardedAd rewardedAd;
    private boolean isLoadingAd = false;

    // ⚠️ Укажи сюда свой Ad Unit ID (Rewarded)
    private static final String REWARDED_AD_UNIT_ID =
        System.getenv("REWARDED_AD_UNIT_ID");

    public AdsBridge(Activity activity) {
        this.activity = activity;
        MobileAds.initialize(activity, initializationStatus -> {
            Log.d(TAG, "MobileAds initialized");
        });
    }

    public void showRewarded() {
        if (isLoadingAd) {
            Log.d(TAG, "Already loading ad...");
            return;
        }
        isLoadingAd = true;
        AdRequest adRequest = new AdRequest.Builder().build();

        RewardedAd.load(activity, REWARDED_AD_UNIT_ID, adRequest, new RewardedAdLoadCallback() {
            @Override
            public void onAdLoaded(RewardedAd ad) {
                Log.d(TAG, "Rewarded ad loaded");
                isLoadingAd = false;
                rewardedAd = ad;
                showAdNow();
            }

            @Override
            public void onAdFailedToLoad(LoadAdError adError) {
                Log.e(TAG, "Failed to load rewarded ad: " + adError.getMessage());
                isLoadingAd = false;
            }
        });
    }

    private void showAdNow() {
        if (rewardedAd == null) {
            Log.e(TAG, "Rewarded ad is not ready");
            return;
        }

        rewardedAd.setFullScreenContentCallback(new FullScreenContentCallback() {
            @Override
            public void onAdShowedFullScreenContent() {
                Log.d(TAG, "Ad showed fullscreen content");
            }

            @Override
            public void onAdDismissedFullScreenContent() {
                Log.d(TAG, "Ad dismissed");
                rewardedAd = null;  // чтобы потом можно было загрузить новую
            }

            @Override
            public void onAdFailedToShowFullScreenContent(com.google.android.gms.ads.AdError adError) {
                Log.e(TAG, "Ad failed to show: " + adError.getMessage());
                rewardedAd = null;
            }
        });

        rewardedAd.show(activity, rewardItem -> {
            Log.d(TAG, "User earned reward: " + rewardItem.getAmount());
            try {
                org.kivy.android.Python py = org.kivy.android.Python.getInstance();
                py.getModule("ads").callAttr("on_android_reward_received");
            } catch (Exception e) {
                Log.e(TAG, "Failed to call Python reward callback", e);
            }
        });
    }
}
