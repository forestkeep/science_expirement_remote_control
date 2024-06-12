unit Main;

interface

uses
  Windows, Messages, SysUtils, Classes, Graphics, Controls, Forms, Dialogs,
  StdCtrls, Buttons, OoMisc, AdPort, ExtCtrls, Math;

type
  TForm1 = class(TForm)
    BitBtn1: TBitBtn;
    BitBtn2: TBitBtn;
    BitBtn3: TBitBtn;
    BitBtn4: TBitBtn;
    BitBtn5: TBitBtn;
    BitBtn6: TBitBtn;
    BitBtn7: TBitBtn;
    BitBtn8: TBitBtn;
    BitBtn9: TBitBtn;
    BitBtn10: TBitBtn;
    BitBtn11: TBitBtn;
    BitBtn12: TBitBtn;
    BitBtn13: TBitBtn;
    BitBtn14: TBitBtn;
    BitBtn15: TBitBtn;
    BitBtn16: TBitBtn;
    BitBtn17: TBitBtn;
    ApdComPort1: TApdComPort;
    Timer1: TTimer;
    Label1: TLabel;
    Label2: TLabel;
    Label3: TLabel;
    Panel2: TPanel;
    Panel1: TPanel;
    DQValue: TLabel;
    RLC: TLabel;
    DQ: TLabel;
    RLCValue: TLabel;
    Limit: TLabel;
    Level: TLabel;
    Frequency: TLabel;
    Offset: TLabel;
    Label4: TLabel;
    Label5: TLabel;
    Label6: TLabel;
    Label7: TLabel;
    Flash: TLabel;
    procedure ApdComPort1Trigger(CP: TObject; Msg, TriggerHandle,
      Data: Word);
    procedure FormCreate(Sender: TObject);
    procedure ErrorComm;
    procedure CalcValue;
    procedure Timer1Timer(Sender: TObject);
    procedure BitBtn16Click(Sender: TObject);
    procedure BitBtn4Click(Sender: TObject);
    procedure BitBtn8Click(Sender: TObject);
    procedure BitBtn12Click(Sender: TObject);
    procedure BitBtn3Click(Sender: TObject);
    procedure BitBtn2Click(Sender: TObject);
    procedure BitBtn1Click(Sender: TObject);
    procedure BitBtn5Click(Sender: TObject);
    procedure BitBtn6Click(Sender: TObject);
    procedure BitBtn7Click(Sender: TObject);
    procedure BitBtn9Click(Sender: TObject);
    procedure BitBtn10Click(Sender: TObject);
    procedure BitBtn11Click(Sender: TObject);
    procedure BitBtn13Click(Sender: TObject);
    procedure BitBtn14Click(Sender: TObject);
    procedure BitBtn15Click(Sender: TObject);

  private
    { Private declarations }
  public
    { Public declarations }
  end;

var
  Form1: TForm1;
  BlockIn: array [0..21] of byte;
  FlashF: boolean;

implementation

{$R *.DFM}



procedure TForm1.ApdComPort1Trigger(CP: TObject; Msg, TriggerHandle,
  Data: Word);
var
   CheckSum,i: byte;
begin
     if ApdComPort1.InBuffUsed >= 22 then
                                       begin
                                       ApdComPort1.GetBlock(BlockIn,22);
                                       CheckSum:=0;
                                       for i:=0 to 20 do
                                           CheckSum:=CheckSum+BlockIn[i];
                                       if (BlockIn[0]=$aa) and (CheckSum=BlockIn[21])
                                          then
                                              begin
                                              ApdComPort1.FlushInBuffer;
                                              Timer1.Enabled:=false;
                                              CalcValue;
                                              Timer1.Enabled:=true;
                                              if FlashF then begin
                                                                 Flash.Visible:=true;
                                                                 FlashF:=false;
                                                                 end
                                                        else begin
                                                                  Flash.Visible:=false;
                                                                  FlashF:=true;
                                                                  end;
                                              end;
                                       ApdComPort1.FlushInBuffer;
//                                       Memo1.Clear;
//                                       for i:=0 to 20 do
//                                          Memo1.Lines.Add(IntToHex(blockIn[i],2))
                                       end;

end;

procedure TForm1.FormCreate(Sender: TObject);
begin
     if ApdComPort1.Open=false then begin
                                    ApdComPort1.Open:=true;
                                    end;
     Timer1.Enabled:=true;
end;



procedure TForm1.ErrorComm;
begin
     RLCValue.Caption:='Comm Error';
end;

procedure TForm1.CalcValue;
var
   RLCVal, DQVal: real;
   m: byte;
   Lev: real;
   Freq: integer;
   Text,Units: string;
begin
     case BlockIn[10] of
          0: RLC.Caption:='Cp';
          1: RLC.Caption:='Lp';
          2: RLC.Caption:='Rp';
          3: RLC.Caption:='Gp';
          4: RLC.Caption:='Bp';
          5: RLC.Caption:='Y';
          6: RLC.Caption:='Q';
          7: RLC.Caption:='Cs';
          8: RLC.Caption:='Ls';
          9: RLC.Caption:='Rs';
          10: RLC.Caption:='T';
          11: RLC.Caption:='Xs';
          12: RLC.Caption:='Z';
          13: RLC.Caption:='D';
          14: RLC.Caption:='I';
     end;
     case BlockIn[10] of
          0: Units:='F';
          1: Units:='H';
          2: Units:='Om';
          3: Units:='S';
          4: Units:='S';
          5: Units:='S';
          6: Units:=' ';
          7: Units:='F';
          8: Units:='H';
          9: Units:='Om';
          10: Units:='°';
          11: Units:='Om';
          12: Units:='Om';
          13: Units:=' ';
          14: Units:='A';
     end;
          if (BlockIn[18] and 128)<>0 then
        begin
            BlockIn[16]:=BlockIn[16] xor 255;
            BlockIn[17]:=BlockIn[17] xor 255;
            BlockIn[18]:=BlockIn[18] xor 255;
            RLCVal:=-1-BlockIn[16]-(BlockIn[17]+BlockIn[18]*256)*256;
        end
        else begin
                  RLCVal:=BlockIn[16]+(BlockIn[17]+BlockIn[18]*256)*256;
             end;
//        RLCVal:=RLCVal*Power(10,BlockIn[19]);
        case BlockIn[19] of
          0: begin
                  m:=2;
                  Text:='k';
                  end;
          1: begin
                  m:=3;
                  Text:='k';
                  end;
          2: begin
                  m:=4;
                  Text:='k';
                  end;
          3: begin
                  m:=2;
                  Text:='M';
                  end;
          4: begin
                  m:=3;
                  Text:='M';
                  end;
          5: begin
                  m:=4;
                  Text:='M';
                  end;
          6: begin
                  m:=2;
                  Text:='G';
                  end;
          7: begin
                  m:=3;
                  Text:='G';
                  end;
          8: begin
                  m:=4;
                  Text:='G';
                  end;
          9: begin
                  m:=2;
                  Text:='T';
                  end;
          10: begin
                  m:=3;
                  Text:='T';
                  end;
          11: begin
                  m:=4;
                  Text:='T';
                  end;
          12: begin
                  m:=2;
                  Text:='T';
                  end;
          13: begin
                  m:=3;
                  Text:='T';
                  end;
          14: begin
                  m:=4;
                  Text:='T';
                  end;
          $ff: begin
                  m:=4;
                  Text:=' ';
                  end;
          $fe: begin
                  m:=3;
                  Text:=' ';
                  end;
          $fd: begin
                  m:=2;
                  Text:=' ';
                  end;
          $fc: begin
                  m:=4;
                  Text:='m';
                  end;
          $fb: begin
                  m:=3;
                  Text:='m';
                  end;
          $fa: begin
                  m:=2;
                  Text:='m';
                  end;
          $f9: begin
                  m:=4;
                  Text:='mk';
                  end;
          $f8: begin
                  m:=3;
                  Text:='mk';
                  end;
          $f7: begin
                  m:=2;
                  Text:='mk';
                  end;
          $f6: begin
                  m:=4;
                  Text:='n';
                  end;
          $f5: begin
                  m:=3;
                  Text:='n';
                  end;
          $f4: begin
                  m:=2;
                  Text:='n';
                  end;
          $f3: begin
                  m:=4;
                  Text:='p';
                  end;
          $f2: begin
                  m:=3;
                  Text:='p';
                  end;
          $f1: begin
                  m:=2;
                  Text:='p';
                  end;
          $f0: begin
                  m:=4;
                  Text:='f';
                  end;
          $ef: begin
                  m:=3;
                  Text:='f';
                  end;
          $ee: begin
                  m:=2;
                  Text:='f';
                  end;
          $ed: begin
                  m:=4;
                  Text:='f';
                  end;
          $ec: begin
                  m:=3;
                  Text:='f';
                  end;
          $eb: begin
                  m:=2;
                  Text:='f';
                  end;
        end;
        RLCVal:=RLCVal/Power(10,5-m);
        RLCValue.Caption:=format('%*.*f',[m,5-m,RLCVal])+' '+Text+Units;
     if (BlockIn[14] and 128) <>0 then
        begin
            BlockIn[12]:=BlockIn[12] xor 255;
            BlockIn[13]:=BlockIn[13] xor 255;
            BlockIn[14]:=BlockIn[14] xor 255;
            DQVal:=-1-BlockIn[12]-(BlockIn[13]+BlockIn[14]*256)*256;
        end
        else begin
                  DQVal:=BlockIn[12]+(BlockIn[13]+BlockIn[14]*256)*256;
             end;
        case BlockIn[15] of
          0: m:=1;
          1: m:=2;
          2: m:=3;
          3: m:=4;
          4: m:=3;
          5: m:=4;
          6: m:=2;
          7: m:=3;
          8: m:=4;
          9: m:=2;
          10: m:=3;
          11: m:=4;
          12: m:=2;
          13: m:=3;
          14: m:=4;
          $ff: m:=4;
          $fe: m:=3;
          $fd: m:=2;
          $fc: m:=1;
          $fb: m:=4;
          $fa: m:=3;
          $f9: m:=2;
          $f8: m:=1;
          $f7: m:=2;
          $f6: m:=4;
          $f5: m:=3;
          $f4: m:=2;
          $f3: m:=4;
          $f2: m:=3;
          $f1: m:=2;
          $f0: m:=4;
          $ef: m:=3;
          $ee: m:=2;
          $ed: m:=4;
          $ec: m:=3;
          $eb: m:=2;
        end;
     case BlockIn[11] of
          0: Units:='F';
          1: Units:='H';
          2: Units:='Om';
          3: Units:='S';
          4: Units:='S';
          5: Units:='S';
          6: Units:=' ';
          7: Units:='F';
          8: Units:='H';
          9: Units:='Om';
          10: Units:='°';
          11: Units:='Om';
          12: Units:='Om';
          13: Units:=' ';
          14: Units:='A';
     end;
     case BlockIn[15] of
          0: Text:='k';
          1: Text:='k';
          2: Text:='k';
          3: Text:='M';
          4: Text:='M';
          5: Text:='M';
          6: Text:='G';
          7: Text:='G';
          8: Text:='G';
          9: Text:='T';
          10: Text:='T';
          11: Text:='T';
          12: Text:='T';
          13: Text:='T';
          14: Text:='T';
          $ff: Text:=' ';
          $fe: Text:=' ';
          $fd: Text:=' ';
          $fc: Text:='m';
          $fb: Text:='m';
          $fa: Text:='m';
          $f9: Text:='mk';
          $f8: Text:='mk';
          $f7: Text:='mk';
          $f6: Text:='n';
          $f5: Text:='n';
          $f4: Text:='n';
          $f3: Text:='p';
          $f2: Text:='p';
          $f1: Text:='p';
          $f0: Text:='f';
          $ef: Text:='f';
          $ee: Text:='f';
          $ed: Text:='f';
          $ec: Text:='f';
          $eb: Text:='f';
        end;
        if BlockIn[11]=13 then Text:=' ';
        if BlockIn[11]=6 then Text:=' ';
        DQVal:=DQVal/Power(10,5-m);
        DQValue.Caption:=format('%*.*f',[m,5-m,DQVal])+' '+Text+Units;

     if BlockIn[10]=14 then begin
                                 DQ.Visible:=false;
                                 DQValue.Visible:=false;
                                 Level.Visible:=false;
                                 Frequency.Visible:=false;
                                 end
                       else begin
                                 DQ.Visible:=true;
                                 DQValue.Visible:=true;
                                 Level.Visible:=true;
                                 Frequency.Visible:=true;
                                 end;
     case BlockIn[11] of
          0: DQ.Caption:='Cp';
          1: DQ.Caption:='Lp';
          2: DQ.Caption:='Rp';
          3: DQ.Caption:='Gp';
          4: DQ.Caption:='Bp';
          5: DQ.Caption:='Y';
          6: DQ.Caption:='Q';
          7: DQ.Caption:='Cs';
          8: DQ.Caption:='Ls';
          9: DQ.Caption:='Rs';
          10: DQ.Caption:='F';
          11: DQ.Caption:='Xs';
          12: DQ.Caption:='Z';
          13: DQ.Caption:='D';
          14: DQ.Caption:='I';
     end;
     if (BlockIn[7] and 2)<>0 then                     //предел
                        Limit.Caption:='A '
                    else
                        Limit.Caption:='   ';
     if BlockIn[10]=14 then
                       case BlockIn[9] of
                            0: Text:='Error';
                            1: Text:='1mkA';
                            2: Text:='10mkA';
                            3: Text:='100mkA';
                            4: Text:='1mA';
                            5: Text:='10mA';
                            6: Text:='100mA';
                            7: Text:='1A';
                            8: Text:='10A';
                            end
                       else
                       case BlockIn[9] of
                            0: Text:='Error';
                            1: Text:='10MOm';
                            2: Text:='1MOm';
                            3: Text:='100kOm';
                            4: Text:='10kOm';
                            5: Text:='1kOm';
                            6: Text:='100Om';
                            7: Text:='10Om';
                            8: Text:='1Om';
                            end;
     Limit.Caption:=Limit.Caption+Text;

     Lev:=BlockIn[3]/100;                              //Уровень
     Level.Caption:=format('%1.2f',[Lev])+'V';

     Freq:=BlockIn[4]+BlockIn[5]*256;                  //Частота
     case BlockIn[6] of
          0: Text:='Hz';
          3: Text:='kHz';
          6: Text:='MHz';
     end;
     Frequency.Caption:=IntToStr(Freq)+Text;

     Lev:=(blockIn[1]+BlockIn[2]*256)/100;
     Offset.Caption:=format('%2.2f',[Lev])+'V';

     if (BlockIn[20] and 8)<>0 then Label4.Visible:=true
        else Label4.Visible:=false;
     if (BlockIn[20] and 1)<>0 then Label5.Visible:=true
        else Label5.Visible:=false;
     if (BlockIn[20] and 4)<>0 then Label6.Visible:=true
        else Label6.Visible:=false;
     if (BlockIn[20] and 2)<>0 then Label7.Visible:=true
        else Label7.Visible:=false;
end;

procedure TForm1.Timer1Timer(Sender: TObject);
begin
     ErrorComm;
end;

procedure TForm1.BitBtn16Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($f));
end;

procedure TForm1.BitBtn4Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($3));
end;

procedure TForm1.BitBtn8Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($7));
end;

procedure TForm1.BitBtn12Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($b));
end;

procedure TForm1.BitBtn3Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($2));
end;

procedure TForm1.BitBtn2Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($1));
end;

procedure TForm1.BitBtn1Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($0));
end;

procedure TForm1.BitBtn5Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($4));
end;

procedure TForm1.BitBtn6Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($5));
end;

procedure TForm1.BitBtn7Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($6));
end;

procedure TForm1.BitBtn9Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($8));
end;

procedure TForm1.BitBtn10Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($9));
end;

procedure TForm1.BitBtn11Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($a));
end;

procedure TForm1.BitBtn13Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($c));
end;

procedure TForm1.BitBtn14Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($d));
end;

procedure TForm1.BitBtn15Click(Sender: TObject);
begin
     ApdComPort1.PutChar(Chr($e));
end;

end.
