'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 300000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 5.0.8
' Optimize                       = Yes
' Optimize_Level                 = 1
' Info_Last_Save                 = DUTTLAB8-PC  Duttlab8-PC\Duttlab8
'<Header End>
' TrialCounter.bas
'
' H.M.   22.06.1999   creation
' R.Ra   16.03.2004   cnt_se_diff(3) added
'
' Demo program for ADwin-Gold up/down counters 
' par_1 = cnt#1
' par_2 = cnt#2
' par_3 = cnt#3
' par_4 = cnt#4

#Include ADwinGoldII.inc


init:
  Cnt_Enable(0)
  Cnt_Clear(1)           ' Clear counter 1
  Cnt_Mode(1,8)          ' Counter input external
  Cnt_Enable(1)         ' enable counter 1



event:
  par_1 = Cnt_Read(1)
  Cnt_Clear(1)




finish:
  Cnt_Enable(0)
