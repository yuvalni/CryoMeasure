close all
clear all
clc
%%  Get  Data
cd('C:\Users\Amit\Documents\CryoMeasure\Calibration');

T_Cernox=readtable('Cernox_calibration.dat');
R_Cernox=table2array(T_Cernox(1:60,20));
Temp_Cernox=table2array(T_Cernox(1:60,4));

T_Diode=readtable('LS_Diode_Calibration.dat');
R_Diode=table2array(T_Diode(:,22));
Temp_Diode=table2array(T_Diode(:,4));

figure (1)
[p_Cernox,S_Cernox,mu_Cernox] = polyfit(R_Cernox(16:60),Temp_Cernox(16:60),10);
poly_Cernox = polyval(p_Cernox,R_Cernox(16:60));
plot(R_Cernox(16:60),Temp_Cernox(16:60),'.-',R_Cernox(16:60),poly_Cernox,'x-')
xlim([0 3000])
ylim([0 110])
legend('Data Cernox','poly Cernox')
grid on
title('Cernox')
xlabel('R [\Omega]') 
ylabel('Temp [K]')

figure (2)
[p_Diode,S_Diode,mu_Diode] = polyfit(R_Diode,Temp_Diode,10);
plot(R_Diode,Temp_Diode,'.')
grid on
title('Diode')
xlabel('R [\Omega]') 
ylabel('Temp [K]')

%part 1  Temp(1:22): 300-64 [K]

%      p1 =  -6.884e-18  (-1.085e-17, -2.918e-18)
%        p2 =   1.222e-14  (5.672e-15, 1.878e-14)
%        p3 =  -9.538e-12  (-1.426e-11, -4.819e-12)
%        p4 =   4.294e-09  (2.351e-09, 6.237e-09)
%        p5 =  -1.231e-06  (-1.734e-06, -7.275e-07)
%        p6 =   0.0002336  (0.0001485, 0.0003187)
%        p7 =    -0.02951  (-0.03888, -0.02014)
%        p8 =       2.421  (1.773, 3.069)
%        p9 =      -120.6  (-146.1, -95.13)
%        p10 =        3089  (2654, 3523)



%part 2  Temp(20:52): 74-7.1 [K]
% Coefficients (with 95% confidence bounds):
%        p1 =  -4.519e-25  (-5.281e-25, -3.758e-25)
%        p2 =   4.029e-21  (3.406e-21, 4.652e-21)
%        p3 =  -1.568e-17  (-1.787e-17, -1.348e-17)
%        p4 =   3.499e-14  (3.063e-14, 3.934e-14)
%        p5 =  -4.945e-11  (-5.48e-11, -4.41e-11)
%        p6 =   4.611e-08  (4.189e-08, 5.032e-08)
%        p7 =  -2.861e-05  (-3.073e-05, -2.65e-05)
%        p8 =     0.01161  (0.01096, 0.01227)
%        p9 =      -2.919  (-3.031, -2.808)
%        p10 =       389.6  (381.5, 397.6)

