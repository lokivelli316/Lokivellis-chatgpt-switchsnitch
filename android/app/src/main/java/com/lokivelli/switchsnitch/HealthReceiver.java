package com.lokivelli.switchsnitch;
import android.app.*;
import android.content.*;
import android.os.*;
public class HealthReceiver extends BroadcastReceiver {
 static void schedule(Context c){AlarmManager a=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);PendingIntent pi=PendingIntent.getBroadcast(c,61,new Intent(c,HealthReceiver.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);a.setInexactRepeating(AlarmManager.ELAPSED_REALTIME_WAKEUP,SystemClock.elapsedRealtime()+60000,60000,pi);}
 @Override public void onReceive(Context c,Intent i){schedule(c);long last=c.getSharedPreferences("snitch",0).getLong("heartbeat",0);if(System.currentTimeMillis()-last>120000)WatchService.notice(c,72,"SwitchSnitch observer unavailable","Accessibility service stopped, disabled or delayed. Model lock is not verified.",true);}
}
