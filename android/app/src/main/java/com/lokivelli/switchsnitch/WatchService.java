package com.lokivelli.switchsnitch;
import android.accessibilityservice.AccessibilityService;
import android.app.*;
import android.content.*;
import android.graphics.Rect;
import android.os.*;
import android.view.accessibility.*;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import org.json.JSONObject;

public class WatchService extends AccessibilityService {
 static final String PKG="com.openai.chatgpt", UNKNOWN="UNVERIFIED";
 final Handler ui=new Handler(Looper.getMainLooper());
 final ExecutorService net=Executors.newSingleThreadExecutor();
 android.content.SharedPreferences p;
 String surface, last="", delivered="", lastStatus=""; long since, lastSent; boolean busy, restoring;
 String predecessor="";
 static final class Snapshot {String model=UNKNOWN,chat="",diag=""; AccessibilityNodeInfo picker;}
 static String norm(CharSequence s){return s==null?"":s.toString().trim().replaceAll("\\s+"," ");}
 static boolean modelLabel(String x){return x.matches("(?i)GPT[- ]?[0-9]+(?:\\.[0-9]+)?(?:[ -](?:Sol|Thinking|Instant|Pro|Auto|Medium|High|Extra High|Mini|Nano))*");}
 static boolean eq(String a,String b){return a.equalsIgnoreCase(b);}
 static boolean opaque(String x){return x.matches("(?i)(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|(?:chat|conv)[_-][A-Za-z0-9_-]{12,100})");}
 static void notice(Context c,int id,String title,String body,boolean ongoing){
  NotificationManager nm=(NotificationManager)c.getSystemService(Context.NOTIFICATION_SERVICE);
  String channel=id==71?"mismatch": "health";
  nm.createNotificationChannel(new NotificationChannel(channel,id==71?"Model mismatch":"Observer health",id==71?NotificationManager.IMPORTANCE_HIGH:NotificationManager.IMPORTANCE_DEFAULT));
  Intent target=id==71?c.getPackageManager().getLaunchIntentForPackage(PKG):new Intent(c,MainActivity.class);
  if(target==null)target=new Intent(c,MainActivity.class);
  PendingIntent pi=PendingIntent.getActivity(c,id,target,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
  try{nm.notify(id,new Notification.Builder(c,channel).setSmallIcon(android.R.drawable.stat_sys_warning).setContentTitle(title).setContentText(body).setStyle(new Notification.BigTextStyle().bigText(body)).setContentIntent(pi).setOngoing(ongoing).setOnlyAlertOnce(true).build());}catch(SecurityException ignored){}
 }
 @Override protected void onServiceConnected(){p=getSharedPreferences("snitch",MODE_PRIVATE);surface=p.getString("surface","");if(surface.isEmpty()){surface="android-"+UUID.randomUUID();p.edit().putString("surface",surface).apply();}HealthReceiver.schedule(this);ui.removeCallbacks(tick);ui.post(tick);}
 @Override public void onAccessibilityEvent(AccessibilityEvent e){}
 @Override public void onInterrupt(){state("INTERRUPTED","Accessibility interrupted");}
 @Override public void onDestroy(){ui.removeCallbacksAndMessages(null);net.shutdownNow();if(p!=null)state("STOPPED","Accessibility service stopped");super.onDestroy();}
 final Runnable tick=new Runnable(){public void run(){try{observe();}catch(Exception e){state("OBSERVER_ERROR",e.getClass().getSimpleName());}finally{ui.postDelayed(this,1500);}}};
 void state(String s,String diag){if(p==null)return;p.edit().putString("state",s).putString("diagnostic",diag).putLong("heartbeat",System.currentTimeMillis()).apply();
  if(!s.equals(lastStatus)){lastStatus=s;notice(this,72,"SwitchSnitch: "+s,diag,true);}
 }
 Snapshot snapshot(){Snapshot out=new Snapshot();AccessibilityNodeInfo root=getRootInActiveWindow();if(root==null||!PKG.equals(norm(root.getPackageName())))return out;
  Rect screen=new Rect();root.getBoundsInScreen(screen);String mid=p.getString("model_id",""),cid=p.getString("chat_id","");
  if(!cid.isEmpty()){List<AccessibilityNodeInfo> ns=root.findAccessibilityNodeInfosByViewId(cid);if(ns.size()==1){String val=norm(ns.get(0).getContentDescription());if(!opaque(val))val=norm(ns.get(0).getText());if(opaque(val))out.chat=val;}}
  ArrayDeque<AccessibilityNodeInfo> q=new ArrayDeque<>();q.add(root);int n=0;List<AccessibilityNodeInfo> matches=new ArrayList<>();Set<String> ids=new LinkedHashSet<>();
  while(!q.isEmpty()&&n++<350){AccessibilityNodeInfo a=q.remove();Rect r=new Rect();a.getBoundsInScreen(r);String id=norm(a.getViewIdResourceName());boolean top=r.top>=screen.top&&r.top<screen.top+Math.max(150,screen.height()/5);
   boolean candidate=!mid.isEmpty()?id.equals(mid):top&&id.toLowerCase(Locale.ROOT).matches(".*model.*(?:select|picker|switch|menu|button).*");
   if(candidate&&a.isVisibleToUser()){ids.add(id);String label=norm(a.getText());if(!modelLabel(label))label=norm(a.getContentDescription());if(modelLabel(label)){matches.add(a);out.model=label;}}
   for(int j=0;j<a.getChildCount();j++){AccessibilityNodeInfo child=a.getChild(j);if(child!=null)q.add(child);}
  }
  if(matches.size()==1)out.picker=matches.get(0);else out.model=UNKNOWN;
  out.diag="Model selector IDs: "+String.join(", ",ids)+"; chat identity "+(out.chat.isEmpty()?"UNVERIFIED":"available");
  return out;
 }
 String expected(){return p.getString("expected","GPT-5.6 Sol");}
 String token(){return p.getString("token","");}
 JSONObject call(String path,JSONObject payload,String chat,String exp)throws Exception{
  int port=Integer.parseInt(p.getString("port","8765"));if(port<8765||port>8864)throw new IOException("PORT");
  HttpURLConnection c=(HttpURLConnection)new URL("http://127.0.0.1:"+port+path).openConnection();
  c.setInstanceFollowRedirects(false);c.setConnectTimeout(1200);c.setReadTimeout(1800);c.setRequestProperty("X-SwitchSnitch-Token",token());c.setRequestProperty("X-SwitchSnitch-Surface",surface);c.setRequestProperty("X-SwitchSnitch-Chat",chat);c.setRequestProperty("X-SwitchSnitch-Expected",exp);
  try{if(payload!=null){c.setRequestMethod("POST");c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");try(OutputStream o=c.getOutputStream()){o.write(payload.toString().getBytes(StandardCharsets.UTF_8));}}
   if(c.getResponseCode()!=200)throw new IOException("HTTP "+c.getResponseCode());
   try(InputStream in=c.getInputStream()){ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buf=new byte[2048];int n;while((n=in.read(buf))!=-1){bytes.write(buf,0,n);if(bytes.size()>65536)throw new IOException("RESPONSE_SIZE");}return new JSONObject(bytes.toString("UTF-8"));}
  }finally{c.disconnect();}
 }
 JSONObject obj(Object... pairs){JSONObject j=new JSONObject();try{for(int i=0;i<pairs.length;i+=2)j.put((String)pairs[i],pairs[i+1]);}catch(Exception e){throw new IllegalArgumentException(e);}return j;}
 void observe(){if(p==null)return;Snapshot s=snapshot();String exp=expected(),key=s.chat+"|"+exp+"|"+s.model;
  long t=SystemClock.elapsedRealtime();if(!key.equals(last)){last=key;since=t;delivered="";}
  if(s.model.equals(UNKNOWN)){state("SELECTOR_UNVERIFIED","ChatGPT inactive or model selector not uniquely visible. "+s.diag);}
  else if(exp.equals("UNLOCKED")){state("UNLOCKED",s.diag);}
  else if(s.chat.isEmpty()){state("CHAT_ID_UNVERIFIED",s.diag);}
  else {state("MONITORING_VISIBLE_MODEL",s.diag);}
  if(t-since<700||restoring)return;
  boolean wrong=!s.model.equals(UNKNOWN)&&!exp.equals("UNLOCKED")&&!eq(s.model,exp);
  if(wrong&&!key.equals(delivered)){notice(this,71,"SwitchSnitch: model mismatch","Expected "+exp+"; visible "+s.model+". "+(s.chat.isEmpty()?"Chat ID unavailable: tap to restore manually.":"Termux approval required."),false);}
  if(!wrong)((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).cancel(71);
  if(busy||token().isEmpty())return;busy=true;
  final String chat=s.chat,model=s.model,status=lastStatus;final boolean send=wrong&&!chat.isEmpty()&&(!key.equals(delivered)||t-lastSent>15000);
  net.execute(()->{try{
   call("/surface",obj("state",status),chat,exp);
   if(send){JSONObject e=call("/event",obj("type","MODEL_MISMATCH","surface_id",surface,"chat_id",chat,"expected_at_event",exp,"selected_at_event",model,"observed_at_event",UNKNOWN,"predecessor_id",predecessor),chat,exp);
    if(e.optBoolean("ok"))ui.post(()->{if(last.equals(key)){delivered=key;lastSent=SystemClock.elapsedRealtime();predecessor="";}});}
   if(chat.isEmpty()||!wrong)return;
   JSONObject d=call("/decision",null,chat,exp);if(!"NOOP".equals(d.optString("action")))ui.post(()->decision(d,chat,exp,model));
  }catch(Exception e){ui.post(()->{if(last.equals(key))state("BRIDGE_UNREACHABLE","Native monitor active; Termux transport failed. "+s.diag);});}finally{ui.post(()->busy=false);}});
 }
 void report(String type,String mid,String chat,String exp,String reason,String model){net.execute(()->{try{call("/receipt",obj("event_type",type,"mismatch_id",mid,"reason",reason,"selected_after",model),chat,exp);}catch(Exception e){ui.post(()->state("RECEIPT_DELIVERY_FAILED","Decision receipt transport failed"));}});}
 boolean click(AccessibilityNodeInfo n){for(int i=0;n!=null&&i<4;i++,n=n.getParent())if(n.isClickable()&&n.performAction(AccessibilityNodeInfo.ACTION_CLICK))return true;return false;}
 void decision(JSONObject d,String chat,String exp,String model){String mid=d.optString("mismatch_id"),action=d.optString("action");Snapshot s=snapshot();
  if(!surface.equals(d.optString("surface_id"))||!chat.equals(d.optString("chat_id"))||!chat.equals(s.chat)||!eq(exp,expected())||!eq(model,s.model)||!eq(exp,d.optString("target"))){report("RESTORE_FAILED",mid,chat,exp,"CONTEXT_CHANGED",s.model);predecessor=mid;return;}
  if(action.equals("ACCEPT")){report("ACCEPTED",mid,chat,exp,"OPERATOR_ACCEPTED",s.model);return;}
  if(!action.equals("RESTORE")||restoring)return;restoring=true;
  net.execute(()->{try{call("/receipt",obj("event_type","RESTORE_ATTEMPTED","mismatch_id",mid),chat,exp);ui.post(()->{
    Snapshot now=snapshot();if(!chat.equals(now.chat)||!eq(expected(),exp)||!eq(model,now.model)||now.picker==null||!click(now.picker)){finish(mid,chat,exp,false,"PICKER_OR_CONTEXT_UNAVAILABLE");return;}
    ui.postDelayed(()->choose(mid,chat,exp),450);
   });}catch(Exception e){ui.post(()->finish(mid,chat,exp,false,"RECEIPT_NOT_ACKNOWLEDGED"));}});
 }
 void choose(String mid,String chat,String exp){Snapshot s=snapshot();if(!chat.equals(s.chat)||!eq(exp,expected())){finish(mid,chat,exp,false,"CHAT_ID_OR_EXPECTED_CHANGED");return;}
  AccessibilityNodeInfo root=getRootInActiveWindow();if(root==null||!PKG.equals(norm(root.getPackageName()))){finish(mid,chat,exp,false,"WINDOW_CHANGED");return;}
  List<AccessibilityNodeInfo> opts=root.findAccessibilityNodeInfosByText(exp);List<AccessibilityNodeInfo> hits=new ArrayList<>();for(AccessibilityNodeInfo a:opts)if(a.isVisibleToUser()&&eq(norm(a.getText()),exp)&&!norm(a.getViewIdResourceName()).equals(p.getString("model_id",""))&&a.isClickable())hits.add(a);
  if(hits.size()!=1||!click(hits.get(0))){finish(mid,chat,exp,false,"TARGET_NOT_UNIQUE_OR_UNAVAILABLE");return;}
  verify(mid,chat,exp,SystemClock.elapsedRealtime()+5000);
 }
 void verify(String mid,String chat,String exp,long until){Snapshot s=snapshot();if(!chat.equals(s.chat)||!eq(exp,expected())){finish(mid,chat,exp,false,"CHAT_CHANGED");return;}if(eq(s.model,exp)){finish(mid,chat,exp,true,"VISIBLE_SELECTOR_VERIFIED");return;}if(SystemClock.elapsedRealtime()>=until){finish(mid,chat,exp,false,"VERIFY_TIMEOUT");return;}ui.postDelayed(()->verify(mid,chat,exp,until),250);}
 void finish(String mid,String chat,String exp,boolean ok,String reason){restoring=false;report(ok?"RESTORE_VERIFIED":"RESTORE_FAILED",mid,chat,exp,reason,snapshot().model);if(!ok){predecessor=mid;delivered="";}}
}
