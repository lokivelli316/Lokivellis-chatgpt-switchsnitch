package com.lokivelli.switchsnitch;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.*;
import android.provider.Settings;
import android.graphics.Color;
import android.text.InputType;
import android.widget.*;
public class MainActivity extends Activity {
 android.content.SharedPreferences p; TextView status;
 EditText field(LinearLayout l,String label,String key,String def,boolean secret){
  TextView t=new TextView(this);t.setText(label);t.setTextColor(0xff39ff14);l.addView(t);
  EditText e=new EditText(this);e.setText(p.getString(key,def));e.setSingleLine(true);e.setTextColor(Color.WHITE);
  if(secret)e.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
  l.addView(e);return e;
 }
 @Override public void onCreate(Bundle b){super.onCreate(b);p=getSharedPreferences("snitch",MODE_PRIVATE);
  ScrollView sc=new ScrollView(this);LinearLayout l=new LinearLayout(this);l.setOrientation(1);l.setPadding(28,28,28,28);l.setBackgroundColor(Color.BLACK);sc.addView(l);setContentView(sc);
  TextView title=new TextView(this);title.setText("☢ SWITCHSNITCH // NATIVE ANDROID");title.setTextSize(22);title.setTextColor(0xff00e5ff);l.addView(title);
  status=new TextView(this);status.setTextColor(Color.WHITE);l.addView(status);
  EditText expected=field(l,"Exact expected visible model label","expected","GPT-5.6 Sol",false);
  EditText token=field(l,"Termux token (snitch-token)","token","",true);
  EditText port=field(l,"Termux bridge port (~/.switchsnitch/port)","port","8765",false);
  EditText model=field(l,"Model-selector resource ID (optional, exact)","model_id","",false);
  EditText chat=field(l,"Stable chat-ID resource ID (optional; NOT chat title)","chat_id","",false);
  Button save=new Button(this);save.setText("SAVE CONFIGURATION");l.addView(save);save.setOnClickListener(v->{try{int n=Integer.parseInt(port.getText().toString().trim());if(n<8765||n>8864||expected.getText().toString().trim().isEmpty())throw new IllegalArgumentException();p.edit().putString("expected",expected.getText().toString().trim()).putString("token",token.getText().toString().trim()).putString("port",""+n).putString("model_id",model.getText().toString().trim()).putString("chat_id",chat.getText().toString().trim()).apply();status.setText("Configuration saved. Backend model remains UNVERIFIED.");HealthReceiver.schedule(this);}catch(Exception e){status.setText("Invalid port or expected model");}});
  Button access=new Button(this);access.setText("ENABLE ANDROID ACCESSIBILITY MONITOR");l.addView(access);access.setOnClickListener(v->startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
  Button notif=new Button(this);notif.setText("ENABLE NOTIFICATIONS");l.addView(notif);notif.setOnClickListener(v->{if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},1);else startActivity(new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE,getPackageName()));});
  Button launch=new Button(this);launch.setText("OPEN CHATGPT");l.addView(launch);launch.setOnClickListener(v->{Intent i=getPackageManager().getLaunchIntentForPackage("com.openai.chatgpt");if(i!=null)startActivity(i);});
  TextView note=new TextView(this);note.setTextColor(Color.LTGRAY);note.setText("Native observation is independent of the browser extension. No automatic click without a verified stable chat ID and an approved, unexpired bridge decision. Missing model visibility is an explicit degraded state. Notification permissions and accessibility must be enabled on this device.");l.addView(note);
  HealthReceiver.schedule(this);
 }
 @Override protected void onResume(){super.onResume();if(status!=null)status.setText("Last observer: "+p.getString("state","NOT_CONNECTED")+"\nLast heartbeat: "+p.getLong("heartbeat",0)+"\n"+p.getString("diagnostic","No selector diagnostic yet"));}
}
