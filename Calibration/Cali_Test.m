p_high = coeffvalues(High_Temp_fit)
p_Med = coeffvalues(Med_Temp_fit)
p_Low = coeffvalues(Low_Temp_fit)

RH = linspace(82,325,1000);
RM = linspace(307,1044,1000);
RL = linspace(836,3000,1000);

TH = polyval(p_high,RH);
TM = polyval(p_Med,RM);
TL = polyval(p_Low,RL);

plot(RH,TH)
hold
plot(RM,TM)
plot(RL,TL)

plot(R_Cernox,Temp_Cernox,'O')
legend('High','Med','Low','Measurement')
xlabel("Resistance [Ohm]")
ylabel("Temperature [K]")

figure
scatter(Temp_Cernox,abs(Temp_Cernox-interp1(RH,TH,R_Cernox)))
hold
scatter(Temp_Cernox,abs(Temp_Cernox-interp1(RM,TM,R_Cernox)))
scatter(Temp_Cernox,abs(Temp_Cernox-interp1(RL,TL,R_Cernox)))
set(gca, 'YScale', 'log') 
grid()
legend('High','Med','Low')
xlabel("Temperature [K]")
ylabel("Temperature Error [K]")